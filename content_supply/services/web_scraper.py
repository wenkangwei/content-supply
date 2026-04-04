"""General web page scraper using trafilatura + httpx."""

import logging
import re
from datetime import datetime
from typing import Optional
from urllib import robotparser
from urllib.parse import urlparse

import httpx
import trafilatura

from content_supply.services.rss_crawler import CrawledItem

logger = logging.getLogger(__name__)

# Lightweight regex to pull og:image / twitter:image from raw HTML.
_OG_IMAGE_RE = re.compile(
    r'<meta\s+(?:property|name)=["\'](?:og:image|twitter:image)["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_OG_IMAGE_RE_REV = re.compile(
    r'<meta\s+content=["\']([^"\']+)["\']\s+(?:property|name)=["\'](?:og:image|twitter:image)["\']',
    re.IGNORECASE,
)

# URL patterns that are known to be un-scrapable (dynamic rendering, auth-required, etc.)
_UNSUPPORTED_PATTERNS: list[tuple[str, str]] = [
    (
        r"mp\.weixin\.qq\.com/cgi-bin/",
        "微信公众号后台页面，内容需登录且通过 JS 动态渲染，无法直接抓取。请使用文章链接格式：mp.weixin.qq.com/s/xxx",
    ),
    (
        r"mp\.weixin\.qq\.com/cgi-bin/appmsg\?",
        "微信公众号接口页面，需要登录态，无法直接抓取。请使用文章分享链接：mp.weixin.qq.com/s/xxx",
    ),
    (
        r"login\.|passport\.|auth\.|sso\.",
        "登录/认证页面，无法抓取正文内容",
    ),
    (
        r"\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|gz|tar|mp4|mp3|avi|mov)$",
        "非 HTML 文件（文档/压缩包/视频/音频），暂不支持抓取",
    ),
]


class ScrapeError(Exception):
    """Raised when scraping fails with a user-friendly reason."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class WebScraper:
    """Scrape web pages and extract article content."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def _check_url_supported(self, url: str) -> Optional[str]:
        """Return a reason string if URL is known to be un-scrapable, else None."""
        for pattern, reason in _UNSUPPORTED_PATTERNS:
            if re.search(pattern, url):
                return reason
        return None

    async def scrape(self, url: str, source_name: str = "", check_robots: bool = True) -> Optional[CrawledItem]:
        """Scrape a URL and extract article content.

        Returns ``None`` on any failure (network error, parse failure, etc.).
        Raises ``ScrapeError`` when the URL is known to be un-scrapable.
        """
        # Check for known unsupported URLs
        reason = self._check_url_supported(url)
        if reason:
            raise ScrapeError(reason)

        if check_robots and not self._is_allowed_by_robots(url):
            logger.warning("Blocked by robots.txt: %s", url)
            return None

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    ),
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text

            # Extract content — try site-specific extractors first, then trafilatura ---
            title, content, author, published_at = self._extract_article(html, url)

            if not title and not content:
                logger.info("No useful content extracted from %s", url)
                return None

            # Heuristic: content too short → likely JS-rendered page
            if content and len(content) < 150 and (not title or title == url):
                logger.info("Extracted content too short for JS-rendered page: %s", url)
                return None

            image_url = self._extract_image(html)

            return CrawledItem(
                title=title or url,
                url=url,
                summary="",
                content=content,
                author=author,
                image_url=image_url,
                published_at=published_at,
                source_name=source_name,
            )

        except httpx.HTTPStatusError as exc:
            logger.warning("HTTP error scraping %s: %s", url, exc.response.status_code)
            return None
        except httpx.RequestError as exc:
            logger.warning("Request error scraping %s: %s", url, exc)
            return None
        except Exception:
            logger.error("Unexpected error scraping %s", url, exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_article(self, html: str, url: str) -> tuple[str, str, str, Optional[datetime]]:
        """Extract title, content, author, published_at from HTML.

        Tries site-specific extractors first, falls back to trafilatura.
        Returns (title, content, author, published_at).
        """
        # Site-specific: WeChat article (mp.weixin.qq.com/s/...)
        if "mp.weixin.qq.com" in url:
            result = self._extract_wechat(html)
            if result and result[1]:
                return result

        # Generic: trafilatura
        return self._extract_trafilatura(html)

    def _extract_wechat(self, html: str) -> tuple[str, str, str, Optional[datetime]]:
        """Extract content from WeChat article HTML.

        WeChat articles store body text in <div id="js_content">.
        """
        title = ""
        content = ""
        author = ""
        published_at = None

        # Title: var msg_title = "..." or <h1 class="rich_media_title">
        title_match = re.search(r'var\s+msg_title\s*=\s*"(.*?)"', html)
        if title_match:
            title = title_match.group(1).strip()
        if not title:
            title_match = re.search(
                r'<h1[^>]*class="rich_media_title[^"]*"[^>]*>(.*?)</h1>',
                html, re.DOTALL,
            )
            if title_match:
                title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()

        # Author: var nickname = "..."
        author_match = re.search(r'var\s+nickname\s*=\s*"(.*?)"', html)
        if author_match:
            author = author_match.group(1).strip()

        # Published date: var ct = "..." (unix timestamp) or var publish_time = "..."
        date_match = re.search(r'var\s+publish_time\s*=\s*"(.*?)"', html)
        if date_match:
            from datetime import datetime
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    published_at = datetime.strptime(date_match.group(1).strip(), fmt)
                    break
                except ValueError:
                    continue
        if not published_at:
            ct_match = re.search(r'var\s+ct\s*=\s*"(\d+)"', html)
            if ct_match:
                from datetime import datetime
                try:
                    published_at = datetime.fromtimestamp(int(ct_match.group(1)))
                except (ValueError, OSError):
                    pass

        # Content: <div id="js_content">...</div>
        content_match = re.search(
            r'id="js_content"[^>]*>(.*)</div>\s*(?:<script|<div\s+class="rich_media_tool)',
            html, re.DOTALL,
        )
        if not content_match:
            # Broader fallback: find js_content and capture until the next major section
            content_match = re.search(
                r'id="js_content"[^>]*>(.*?)</div>\s*</div>\s*</div>',
                html, re.DOTALL,
            )
        if content_match:
            raw = content_match.group(1)
            # Clean HTML tags
            content = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
            content = re.sub(r"<p[^>]*>", "\n", content, flags=re.IGNORECASE)
            content = re.sub(r"</p>", "\n", content, flags=re.IGNORECASE)
            content = re.sub(r"<[^>]+>", "", content)
            # Decode HTML entities
            import html as html_mod
            content = html_mod.unescape(content)
            # Normalize whitespace
            content = re.sub(r"[ \t]+", " ", content)
            content = re.sub(r"\n{3,}", "\n\n", content)
            content = content.strip()

        logger.info(
            "WeChat extraction: title=%s, content_len=%d",
            title[:30] if title else "None",
            len(content),
        )
        return title, content, author, published_at

    def _extract_trafilatura(self, html: str) -> tuple[str, str, str, Optional[datetime]]:
        """Extract article content using trafilatura (generic fallback)."""
        content = trafilatura.extract(html) or ""
        title = ""
        author = ""
        published_at = None

        metadata = trafilatura.extract(html, output_format="json")
        if metadata:
            import json

            try:
                meta = json.loads(metadata)
                title = meta.get("title", "") or ""
                author = meta.get("author", "") or ""
                date_str = meta.get("date", "") or ""
                if date_str:
                    from datetime import datetime

                    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                        try:
                            published_at = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
            except (json.JSONDecodeError, TypeError):
                pass

        if not title:
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            if title_match:
                title = title_match.group(1).strip()

        return title, content, author, published_at

    @staticmethod
    def _extract_image(html: str) -> str:
        """Extract main image URL from HTML (og:image or twitter:image)."""
        for pattern in (_OG_IMAGE_RE, _OG_IMAGE_RE_REV):
            match = pattern.search(html)
            if match:
                return match.group(1).strip()
        return ""

    @staticmethod
    def _is_allowed_by_robots(url: str) -> bool:
        """Check if URL is allowed by the site's ``robots.txt``.

        Returns ``True`` by default when the robots file cannot be fetched
        or parsed, so scraping continues unless an explicit disallow is
        found.
        """
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

            rp = robotparser.RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch("ContentSupplyBot", url)
        except Exception:
            # If we cannot fetch / parse robots.txt, default to allow.
            return True

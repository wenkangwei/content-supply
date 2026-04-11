"""General web page scraper using trafilatura + httpx."""

import json
import logging
import re
from datetime import datetime, timezone
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
        self._jimeng_items: list[dict] = []  # Populated after scraping Jimeng pages

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
            self._jimeng_items = []  # Reset for each scrape
            title, content, author, published_at = self._extract_article(html, url)

            if not title and not content:
                logger.info("No useful content extracted from %s", url)
                return None

            # Heuristic: content too short → likely JS-rendered page
            # But skip this check for Jimeng (structured data is stored separately)
            is_jimeng = "jimeng.jianying.com" in url
            if content and len(content) < 150 and (not title or title == url) and not is_jimeng:
                logger.info("Extracted content too short for JS-rendered page: %s", url)
                return None

            image_url = self._extract_image(html)

            # For Jimeng, use first item's cover_url as main image
            if is_jimeng and self._jimeng_items:
                first_cover = self._jimeng_items[0].get("cover_url", "")
                if first_cover:
                    image_url = first_cover

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
        # Site-specific: Jimeng AI artwork gallery (jimeng.jianying.com)
        if "jimeng.jianying.com" in url:
            result = self._extract_jimeng(html, url)
            if result and result[1]:
                return result

        # Site-specific: WeChat article (mp.weixin.qq.com/s/...)
        if "mp.weixin.qq.com" in url:
            result = self._extract_wechat(html)
            if result and result[1]:
                return result

        # Generic: trafilatura
        return self._extract_trafilatura(html)

    # ------------------------------------------------------------------
    # Jimeng (即梦) AI artwork scraper
    # ------------------------------------------------------------------

    def _extract_jimeng(self, html: str, url: str) -> tuple[str, str, str, Optional[datetime]]:
        """Extract AI artwork data from Jimeng (即梦) pages.

        Jimeng is a ByteDance SPA that embeds artwork data as JSON in HTML.
        Homepage: https://jimeng.jianying.com/ai-tool/home
        Detail:   https://jimeng.jianying.com/ai-tool/image/detail/{id}

        Each item has:
        - common_attr: id, title, description, cover_url, cover_url_map, aspect_ratio, create_time
        - aigc_image_params.text2image_params: prompt, seed, (optional) user_negative_prompt
        - author: name, avatar_url
        - image: format, large_images[{width, height}]
        - statistic: usage_num, favorite_num
        """
        title = "即梦 AI 作品"
        content = ""
        author = ""
        published_at = None

        # Find item_list JSON in the SSR data
        item_list_match = re.search(r'"item_list"\s*:\s*\[', html)
        if not item_list_match:
            logger.info("Jimeng: no item_list found in HTML")
            return title, "", author, None

        arr_start = item_list_match.end() - 1
        depth = 0
        arr_end = arr_start
        for i in range(arr_start, min(arr_start + 500000, len(html))):
            if html[i] == '[':
                depth += 1
            elif html[i] == ']':
                depth -= 1
                if depth == 0:
                    arr_end = i + 1
                    break

        try:
            items = json.loads(html[arr_start:arr_end])
        except json.JSONDecodeError:
            logger.warning("Jimeng: failed to parse item_list JSON")
            return title, "", author, None

        if not items:
            return title, "", author, None

        # Build content from items
        parts = [f"即梦 AI 创作广场 — 共获取 {len(items)} 个作品\n"]
        valid_items = []

        for idx, item in enumerate(items):
            ca = item.get("common_attr", {})
            aigc = item.get("aigc_image_params", {})
            t2i = aigc.get("text2image_params") or {}
            author_info = item.get("author", {})
            image_info = item.get("image", {})
            statistic = item.get("statistic", {})

            item_id = ca.get("id", "")
            item_title = ca.get("title", "") or f"作品 #{idx + 1}"
            item_desc = ca.get("description", "")
            prompt = t2i.get("prompt", "")
            negative_prompt = t2i.get("user_negative_prompt", "") or t2i.get("negative_prompt", "")
            cover_url = (ca.get("cover_url") or "").replace("\\u0026", "&")
            aspect_ratio = ca.get("aspect_ratio", "")
            create_time = ca.get("create_time")
            author_name = author_info.get("name", "匿名")
            img_format = image_info.get("format", "")
            large_images = image_info.get("large_images", [])
            usage_num = statistic.get("usage_num", 0)
            favorite_num = statistic.get("favorite_num", 0)
            seed = t2i.get("seed", "")
            model_config = t2i.get("model_config", {})

            # Validate cover_url is accessible
            valid_cover = ""
            if cover_url:
                valid_cover = cover_url

            # Get dimensions from large_images
            width, height = 0, 0
            if large_images:
                li = large_images[0]
                width = li.get("width", 0)
                height = li.get("height", 0)

            # Build cover_url_map with valid URLs
            cover_url_map = {}
            for res, c_url in (ca.get("cover_url_map") or {}).items():
                cover_url_map[res] = c_url.replace("\\u0026", "&")

            # Build text content
            item_parts = [f"## {item_title}"]
            if item_desc:
                item_parts.append(f"描述: {item_desc}")
            if prompt:
                item_parts.append(f"Prompt: {prompt}")
            if negative_prompt:
                item_parts.append(f"Negative Prompt: {negative_prompt}")
            if seed:
                item_parts.append(f"Seed: {seed}")
            item_parts.append(f"作者: {author_name}")
            if width and height:
                item_parts.append(f"尺寸: {width}x{height}")
            item_parts.append(f"格式: {img_format}")
            item_parts.append(f"互动: 使用{usage_num}次, 收藏{favorite_num}次")
            item_parts.append(f"链接: https://jimeng.jianying.com/ai-tool/image/detail/{item_id}")
            if valid_cover:
                item_parts.append(f"图片: {valid_cover}")

            valid_items.append({
                "id": item_id,
                "title": item_title,
                "description": item_desc,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "cover_url": valid_cover,
                "cover_url_map": cover_url_map,
                "aspect_ratio": aspect_ratio,
                "author": author_name,
                "width": width,
                "height": height,
                "format": img_format,
                "seed": str(seed),
                "usage_num": usage_num,
                "favorite_num": favorite_num,
                "create_time": create_time,
                "detail_url": f"https://jimeng.jianying.com/ai-tool/image/detail/{item_id}",
            })

            parts.append("\n".join(item_parts))
            parts.append("---")

        content = "\n\n".join(parts)

        # Use first item's create_time as published_at
        if valid_items and valid_items[0].get("create_time"):
            try:
                published_at = datetime.fromtimestamp(valid_items[0]["create_time"], tz=timezone.utc)
            except (ValueError, OSError):
                pass

        # Store structured data in extra for later use
        self._jimeng_items = valid_items

        logger.info("Jimeng: extracted %d items", len(valid_items))
        return title, content, author, published_at

    async def _validate_image_urls(self, urls: list[str]) -> list[str]:
        """Validate image URLs by checking HTTP HEAD. Return only accessible ones."""
        valid = []
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            for url in urls:
                try:
                    resp = await client.head(url, headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/124.0.0.0 Safari/537.36"
                        ),
                    })
                    if resp.status_code == 200:
                        valid.append(url)
                    else:
                        logger.debug("Image URL returned %d: %s", resp.status_code, url[:100])
                except Exception:
                    logger.debug("Image URL check failed: %s", url[:100])
        return valid

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

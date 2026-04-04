"""General web page scraper using trafilatura + httpx."""

import logging
import re
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


class WebScraper:
    """Scrape web pages and extract article content."""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def scrape(self, url: str, source_name: str = "") -> Optional[CrawledItem]:
        """Scrape a URL and extract article content.

        Returns ``None`` on any failure (network error, parse failure, etc.).
        """
        if not self._is_allowed_by_robots(url):
            logger.warning("Blocked by robots.txt: %s", url)
            return None

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.timeout,
                headers={"User-Agent": "ContentSupplyBot/1.0"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text

            # Extract main article text ---
            content = trafilatura.extract(html) or ""

            # Extract metadata ---
            metadata = trafilatura.extract(html, output_format="json")
            title = ""
            author = ""
            published_at = None

            if metadata:
                import json

                try:
                    meta = json.loads(metadata)
                    title = meta.get("title", "") or ""
                    author = meta.get("author", "") or ""
                    date_str = meta.get("date", "") or ""
                    if date_str:
                        from datetime import datetime

                        for fmt in (
                            "%Y-%m-%d",
                            "%Y-%m-%dT%H:%M:%S",
                            "%Y-%m-%d %H:%M:%S",
                        ):
                            try:
                                published_at = datetime.strptime(date_str, fmt)
                                break
                            except ValueError:
                                continue
                except (json.JSONDecodeError, TypeError):
                    pass

            # Fallback: try to get title from <title> tag
            if not title:
                title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()

            if not title and not content:
                logger.info("No useful content extracted from %s", url)
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

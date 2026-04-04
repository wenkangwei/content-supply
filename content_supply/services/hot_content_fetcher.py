"""Fetch content related to hot keywords."""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import unquote, urlparse

import httpx

from content_supply.services.types import CrawledItem

logger = logging.getLogger(__name__)


class HotContentFetcher:
    """Search and fetch content related to hot keywords."""

    DDG_HTML_URL = "https://html.duckduckgo.com/html/"

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
            )
        return self._client

    async def search_by_keyword(
        self, keyword: str, max_results: int = 5
    ) -> list[str]:
        """Search for article URLs related to a keyword.

        Uses DuckDuckGo HTML search to find related URLs.
        Returns a list of URLs.
        """
        client = self._get_client()
        urls: list[str] = []

        try:
            resp = await client.post(
                self.DDG_HTML_URL,
                data={"q": keyword, "b": ""},
            )
            resp.raise_for_status()
            html = resp.text

            # DuckDuckGo HTML results contain URLs in the form:
            # <a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=ENCODED_URL&amp;rut=...">
            # We parse the uddg parameter from result links.
            pattern = re.compile(r'uddg=([^&"\']+)', re.IGNORECASE)
            matches = pattern.findall(html)

            seen = set()
            for encoded_url in matches:
                url = unquote(encoded_url)
                parsed = urlparse(url)

                # Skip non-http URLs and known non-article domains
                if parsed.scheme not in ("http", "https"):
                    continue
                if not parsed.netloc:
                    continue

                # Deduplicate
                if url in seen:
                    continue
                seen.add(url)
                urls.append(url)

                if len(urls) >= max_results:
                    break

        except Exception as e:
            logger.error("Search failed for keyword '%s': %s", keyword, e)

        return urls

    async def _scrape_url(self, url: str, keyword: str, platform: str) -> Optional[CrawledItem]:
        """Scrape a single URL into a CrawledItem, with basic fallback."""
        try:
            # Try to use WebScraper if available
            from content_supply.services.web_scraper import WebScraper

            scraper = WebScraper()
            item = await scraper.scrape(url, source_name=f"hot:{keyword}")
            if item:
                item.source_type = "hot_keyword"
                item.extra["hot_keyword"] = keyword
                item.extra["hot_platform"] = platform
            return item
        except ImportError:
            # WebScraper not available — use basic httpx fetch
            pass
        except Exception as e:
            logger.warning("WebScraper failed for %s: %s", url, e)

        # Fallback: basic HTTP fetch + minimal extraction
        return await self._basic_scrape(url, keyword, platform)

    async def _basic_scrape(
        self, url: str, keyword: str, platform: str
    ) -> Optional[CrawledItem]:
        """Basic scrape using httpx + regex title/meta extraction."""
        client = self._get_client()
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

            # Extract <title>
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else url

            # Extract meta description
            desc_match = re.search(
                r'<meta\s+[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',
                html,
                re.IGNORECASE,
            )
            if not desc_match:
                desc_match = re.search(
                    r'<meta\s+[^>]*content=["\'](.*?)["\'][^>]*name=["\']description["\']',
                    html,
                    re.IGNORECASE,
                )
            summary = desc_match.group(1).strip() if desc_match else ""

            return CrawledItem(
                title=title,
                url=url,
                summary=summary,
                content=html[:50000],  # Truncate to avoid huge payloads
                source_name=f"hot:{keyword}",
                source_type="hot_keyword",
                extra={
                    "hot_keyword": keyword,
                    "hot_platform": platform,
                },
            )
        except Exception as e:
            logger.warning("Basic scrape failed for %s: %s", url, e)
            return None

    async def fetch_content(
        self, keyword: str, platform: str = "", max_results: int = 5
    ) -> list[CrawledItem]:
        """Search and fetch content for a keyword.

        1. Search for URLs related to the keyword.
        2. For each URL, scrape the content.
        3. Return list of CrawledItem with source_type='hot_keyword'.
        """
        urls = await self.search_by_keyword(keyword, max_results=max_results)
        if not urls:
            logger.info("No URLs found for keyword '%s'", keyword)
            return []

        items: list[CrawledItem] = []
        # Fetch URLs concurrently with a limit
        sem = asyncio.Semaphore(3)

        async def _fetch_one(url: str) -> Optional[CrawledItem]:
            async with sem:
                return await self._scrape_url(url, keyword, platform)

        results = await asyncio.gather(
            *[_fetch_one(u) for u in urls], return_exceptions=True
        )

        for result in results:
            if isinstance(result, CrawledItem):
                items.append(result)

        return items

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

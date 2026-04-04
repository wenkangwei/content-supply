"""Hot keyword tracker — multi-platform adapters."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class HotKeywordItem:
    """A single hot keyword result."""
    keyword: str
    platform: str
    rank: int = 0
    hot_score: float = 0.0
    category: str = ""


class BaseHotAdapter(ABC):
    """Base class for platform-specific hot keyword adapters."""

    platform: str = ""
    _client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self._client

    @abstractmethod
    async def fetch(self) -> list[HotKeywordItem]:
        """Fetch current hot keywords from the platform."""
        ...

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


class HackerNewsAdapter(BaseHotAdapter):
    """Hacker News top stories adapter."""
    platform = "hackernews"

    TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
    ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

    async def fetch(self) -> list[HotKeywordItem]:
        client = self._get_client()
        # Step 1: fetch top story IDs
        resp = await client.get(self.TOP_STORIES_URL)
        resp.raise_for_status()
        story_ids: list[int] = resp.json()

        # Step 2: fetch top 30 items in parallel
        top_ids = story_ids[:30]
        items: list[HotKeywordItem] = []

        async def _fetch_item(rank: int, item_id: int) -> Optional[HotKeywordItem]:
            try:
                r = await client.get(self.ITEM_URL.format(item_id=item_id))
                r.raise_for_status()
                data = r.json()
                if data is None:
                    return None
                return HotKeywordItem(
                    keyword=data.get("title", ""),
                    platform=self.platform,
                    rank=rank,
                    hot_score=float(data.get("score", 0)),
                    category="tech",
                )
            except Exception as e:
                logger.warning("HN item %d fetch failed: %s", item_id, e)
                return None

        coros = [_fetch_item(i + 1, sid) for i, sid in enumerate(top_ids)]
        results = await asyncio.gather(*coros, return_exceptions=True)

        for result in results:
            if isinstance(result, HotKeywordItem) and result.keyword:
                items.append(result)

        return items


class RedditAdapter(BaseHotAdapter):
    """Reddit hot posts adapter."""
    platform = "reddit"

    HOT_URL = "https://www.reddit.com/r/all/hot.json"

    async def fetch(self) -> list[HotKeywordItem]:
        client = self._get_client()
        headers = {"User-Agent": "ContentSupplyBot/1.0 (content aggregation service)"}
        resp = await client.get(self.HOT_URL, headers=headers)
        resp.raise_for_status()

        data = resp.json()
        children = data.get("data", {}).get("children", [])
        items: list[HotKeywordItem] = []

        for idx, child in enumerate(children[:30]):
            post = child.get("data", {})
            title = post.get("title", "")
            score = float(post.get("score", 0))
            if title:
                items.append(HotKeywordItem(
                    keyword=title,
                    platform=self.platform,
                    rank=idx + 1,
                    hot_score=score,
                    category=post.get("subreddit", ""),
                ))

        return items


class GoogleTrendsAdapter(BaseHotAdapter):
    """Google Trends RSS adapter."""
    platform = "google"

    TRENDS_RSS_URL = "https://trends.google.com/trending/rss"

    async def fetch(self) -> list[HotKeywordItem]:
        try:
            import feedparser
        except ImportError:
            logger.error("feedparser is required for Google Trends adapter")
            return []

        client = self._get_client()
        resp = await client.get(self.TRENDS_RSS_URL)
        resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        items: list[HotKeywordItem] = []

        for idx, entry in enumerate(feed.entries[:30]):
            title = entry.get("title", "")
            if title:
                items.append(HotKeywordItem(
                    keyword=title,
                    platform=self.platform,
                    rank=idx + 1,
                    hot_score=0.0,
                    category="general",
                ))

        return items


# Registry of all adapters
ADAPTERS: dict[str, type[BaseHotAdapter]] = {
    "hackernews": HackerNewsAdapter,
    "reddit": RedditAdapter,
    "google": GoogleTrendsAdapter,
}


class HotTracker:
    """Orchestrate hot keyword tracking across platforms."""

    def __init__(self):
        self.adapters: dict[str, BaseHotAdapter] = {
            name: cls() for name, cls in ADAPTERS.items()
        }

    async def fetch_platform(self, platform: str) -> list[HotKeywordItem]:
        """Fetch hot keywords from a specific platform."""
        adapter = self.adapters.get(platform)
        if not adapter:
            logger.warning("Unknown platform: %s", platform)
            return []
        try:
            return await adapter.fetch()
        except Exception as e:
            logger.error("Failed to fetch %s: %s", platform, e)
            return []

    async def fetch_all(
        self, platforms: Optional[list[str]] = None
    ) -> dict[str, list[HotKeywordItem]]:
        """Fetch from all (or specified) platforms concurrently."""
        targets = platforms or list(self.adapters.keys())
        tasks = {p: self.fetch_platform(p) for p in targets}
        coros = await asyncio.gather(*tasks.values(), return_exceptions=True)
        results: dict[str, list[HotKeywordItem]] = {}
        for platform, result in zip(tasks.keys(), coros):
            if isinstance(result, Exception):
                logger.error("%s: %s", platform, result)
                results[platform] = []
            else:
                results[platform] = result
        return results

    async def close(self) -> None:
        """Close all adapter HTTP clients."""
        for adapter in self.adapters.values():
            await adapter.close()

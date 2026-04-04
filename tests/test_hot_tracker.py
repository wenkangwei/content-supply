"""Tests for hot_tracker and hot_content_fetcher modules."""

from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_supply.services.hot_tracker import (
    ADAPTERS,
    HackerNewsAdapter,
    HotKeywordItem,
    HotTracker,
    RedditAdapter,
    GoogleTrendsAdapter,
)
from content_supply.services.hot_content_fetcher import HotContentFetcher
from content_supply.services.types import CrawledItem


# ---------------------------------------------------------------------------
# HotKeywordItem dataclass tests
# ---------------------------------------------------------------------------


class TestHotKeywordItem:
    def test_defaults(self):
        item = HotKeywordItem(keyword="python", platform="reddit")
        assert item.keyword == "python"
        assert item.platform == "reddit"
        assert item.rank == 0
        assert item.hot_score == 0.0
        assert item.category == ""

    def test_full_init(self):
        item = HotKeywordItem(
            keyword="AI", platform="google", rank=1, hot_score=99.5, category="tech"
        )
        assert item.keyword == "AI"
        assert item.rank == 1
        assert item.hot_score == 99.5

    def test_is_dataclass(self):
        item = HotKeywordItem(keyword="test", platform="test")
        d = asdict(item)
        assert "keyword" in d
        assert "platform" in d
        assert "rank" in d


# ---------------------------------------------------------------------------
# HackerNewsAdapter tests
# ---------------------------------------------------------------------------


class TestHackerNewsAdapter:
    @pytest.fixture()
    def mock_top_ids(self):
        """Return a mock topstories.json response (list of IDs)."""
        return [100, 200, 300]

    @pytest.fixture()
    def mock_items(self):
        """Return mock item JSONs."""
        return {
            100: {"id": 100, "title": "Show HN: Python 4.0", "score": 512},
            200: {"id": 200, "title": "Rust is the future", "score": 300},
            300: {"id": 300, "title": "Why Lisp matters", "score": 150},
        }

    @pytest.mark.asyncio
    async def test_fetch_returns_items(self, mock_top_ids, mock_items):
        adapter = HackerNewsAdapter()

        async def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            if "topstories" in url:
                resp.json.return_value = mock_top_ids
                resp.raise_for_status = MagicMock()
            else:
                # Extract item ID from URL
                item_id = int(url.rstrip("/").split("/")[-1].replace(".json", ""))
                resp.json.return_value = mock_items.get(item_id, None)
                resp.raise_for_status = MagicMock()
            return resp

        with patch.object(adapter, "_get_client") as get_client:
            client = AsyncMock()
            client.get = mock_get
            get_client.return_value = client

            results = await adapter.fetch()

        assert len(results) == 3
        assert results[0].keyword == "Show HN: Python 4.0"
        assert results[0].rank == 1
        assert results[0].hot_score == 512.0
        assert results[0].platform == "hackernews"
        assert results[1].rank == 2
        assert results[2].rank == 3

    @pytest.mark.asyncio
    async def test_fetch_empty_response(self):
        adapter = HackerNewsAdapter()

        async def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            if "topstories" in url:
                resp.json.return_value = []
                resp.raise_for_status = MagicMock()
            else:
                resp.json.return_value = None
                resp.raise_for_status = MagicMock()
            return resp

        with patch.object(adapter, "_get_client") as get_client:
            client = AsyncMock()
            client.get = mock_get
            get_client.return_value = client

            results = await adapter.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_skips_items_with_empty_title(self, mock_top_ids):
        mock_items = {
            100: {"id": 100, "title": "", "score": 10},
            200: {"id": 200, "title": "Valid title", "score": 20},
            300: {"id": 300, "title": "Another valid", "score": 30},
        }

        adapter = HackerNewsAdapter()

        async def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            if "topstories" in url:
                resp.json.return_value = mock_top_ids
                resp.raise_for_status = MagicMock()
            else:
                item_id = int(url.rstrip("/").split("/")[-1].replace(".json", ""))
                resp.json.return_value = mock_items.get(item_id, None)
                resp.raise_for_status = MagicMock()
            return resp

        with patch.object(adapter, "_get_client") as get_client:
            client = AsyncMock()
            client.get = mock_get
            get_client.return_value = client

            results = await adapter.fetch()

        # Empty title item should be filtered out
        assert len(results) == 2
        assert results[0].keyword == "Valid title"


# ---------------------------------------------------------------------------
# RedditAdapter tests
# ---------------------------------------------------------------------------


class TestRedditAdapter:
    @pytest.mark.asyncio
    async def test_fetch_returns_items(self):
        adapter = RedditAdapter()
        mock_response = {
            "data": {
                "children": [
                    {"data": {"title": "Python tips", "score": 1000, "subreddit": "python"}},
                    {"data": {"title": "Rust vs Go", "score": 800, "subreddit": "programming"}},
                    {"data": {"title": "AI breakthrough", "score": 500, "subreddit": "MachineLearning"}},
                ]
            }
        }

        async def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = mock_response
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(adapter, "_get_client") as get_client:
            client = AsyncMock()
            client.get = mock_get
            get_client.return_value = client

            results = await adapter.fetch()

        assert len(results) == 3
        assert results[0].keyword == "Python tips"
        assert results[0].rank == 1
        assert results[0].hot_score == 1000.0
        assert results[0].category == "python"
        assert results[1].rank == 2

    @pytest.mark.asyncio
    async def test_fetch_empty_children(self):
        adapter = RedditAdapter()
        mock_response = {"data": {"children": []}}

        async def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = mock_response
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(adapter, "_get_client") as get_client:
            client = AsyncMock()
            client.get = mock_get
            get_client.return_value = client

            results = await adapter.fetch()

        assert results == []


# ---------------------------------------------------------------------------
# HotTracker tests
# ---------------------------------------------------------------------------


class TestHotTracker:
    @pytest.mark.asyncio
    async def test_fetch_platform_unknown(self):
        tracker = HotTracker()
        results = await tracker.fetch_platform("nonexistent_platform")
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_platform_known_adapter_error(self):
        tracker = HotTracker()
        # Patch the hackernews adapter's fetch to raise
        with patch.object(
            tracker.adapters["hackernews"], "fetch", side_effect=Exception("network error")
        ):
            results = await tracker.fetch_platform("hackernews")
        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_all_default_platforms(self):
        tracker = HotTracker()
        mock_items = [HotKeywordItem(keyword="test", platform="mock")]

        with patch.object(tracker.adapters["hackernews"], "fetch", return_value=mock_items), \
             patch.object(tracker.adapters["reddit"], "fetch", return_value=mock_items), \
             patch.object(tracker.adapters["google"], "fetch", return_value=mock_items):
            results = await tracker.fetch_all()

        # Should have results for all 3 platforms
        assert set(results.keys()) == {"hackernews", "reddit", "google"}
        for platform_items in results.values():
            assert len(platform_items) == 1
            assert platform_items[0].keyword == "test"

    @pytest.mark.asyncio
    async def test_fetch_all_specific_platforms(self):
        tracker = HotTracker()
        mock_items = [HotKeywordItem(keyword="specific", platform="reddit")]

        with patch.object(tracker.adapters["reddit"], "fetch", return_value=mock_items):
            results = await tracker.fetch_all(platforms=["reddit"])

        assert "reddit" in results
        assert results["reddit"][0].keyword == "specific"
        assert "hackernews" not in results
        assert "google" not in results

    @pytest.mark.asyncio
    async def test_fetch_all_handles_exception(self):
        tracker = HotTracker()

        with patch.object(
            tracker.adapters["hackernews"], "fetch", side_effect=Exception("fail")
        ):
            with patch.object(
                tracker.adapters["reddit"], "fetch", return_value=[HotKeywordItem(keyword="ok", platform="reddit")]
            ):
                with patch.object(
                    tracker.adapters["google"], "fetch", return_value=[]
                ):
                    results = await tracker.fetch_all()

        assert results["hackernews"] == []
        assert len(results["reddit"]) == 1
        assert results["google"] == []


# ---------------------------------------------------------------------------
# HotContentFetcher tests
# ---------------------------------------------------------------------------


class TestHotContentFetcher:
    @pytest.mark.asyncio
    async def test_search_by_keyword_returns_list(self):
        fetcher = HotContentFetcher()

        html_response = '''
        <html><body>
        <a rel="nofollow" class="result__a"
           href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Farticle1&amp;rut=abc">Result 1</a>
        <a rel="nofollow" class="result__a"
           href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Farticle2&amp;rut=def">Result 2</a>
        </body></html>
        '''

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response
        mock_resp.raise_for_status = MagicMock()

        with patch.object(fetcher, "_get_client") as get_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            get_client.return_value = client

            urls = await fetcher.search_by_keyword("python")

        assert isinstance(urls, list)
        assert len(urls) == 2
        assert "https://example.com/article1" in urls
        assert "https://example.com/article2" in urls

    @pytest.mark.asyncio
    async def test_search_by_keyword_respects_max_results(self):
        fetcher = HotContentFetcher()

        html_response = '''
        <html><body>
        <a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2F1&amp;x=1">1</a>
        <a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2F2&amp;x=2">2</a>
        <a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2F3&amp;x=3">3</a>
        </body></html>
        '''

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = html_response
        mock_resp.raise_for_status = MagicMock()

        with patch.object(fetcher, "_get_client") as get_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            get_client.return_value = client

            urls = await fetcher.search_by_keyword("test", max_results=2)

        assert len(urls) == 2

    @pytest.mark.asyncio
    async def test_search_by_keyword_empty_on_error(self):
        fetcher = HotContentFetcher()

        with patch.object(fetcher, "_get_client") as get_client:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=Exception("connection failed"))
            get_client.return_value = client

            urls = await fetcher.search_by_keyword("nonexistent")

        assert urls == []

    @pytest.mark.asyncio
    async def test_fetch_content_returns_crawled_items(self):
        fetcher = HotContentFetcher()

        search_urls = ["https://example.com/article1"]

        html_content = "<html><head><title>Test Article</title><meta name='description' content='A test article.'></head><body>Content here.</body></html>"

        async def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.text = html_content
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(fetcher, "search_by_keyword", return_value=search_urls):
            # Block WebScraper import to force fallback to _basic_scrape
            import builtins
            real_import = builtins.__import__
            def mock_import(name, *args, **kwargs):
                if "web_scraper" in name:
                    raise ImportError("mocked")
                return real_import(name, *args, **kwargs)
            with patch("builtins.__import__", side_effect=mock_import):
                with patch.object(fetcher, "_get_client") as get_client:
                    client = AsyncMock()
                    client.get = mock_get
                    get_client.return_value = client

                    items = await fetcher.fetch_content("python", platform="reddit")

        assert len(items) == 1
        assert items[0].title == "Test Article"
        assert items[0].source_type == "hot_keyword"
        assert items[0].extra["hot_keyword"] == "python"
        assert items[0].extra["hot_platform"] == "reddit"

    @pytest.mark.asyncio
    async def test_fetch_content_empty_when_no_urls(self):
        fetcher = HotContentFetcher()

        with patch.object(fetcher, "search_by_keyword", return_value=[]):
            items = await fetcher.fetch_content("obscure_keyword")

        assert items == []

    @pytest.mark.asyncio
    async def test_fetch_content_handles_scrape_failure(self):
        fetcher = HotContentFetcher()

        search_urls = ["https://example.com/fail"]

        async def mock_get(url, **kwargs):
            raise Exception("timeout")

        with patch.object(fetcher, "search_by_keyword", return_value=search_urls):
            with patch.object(fetcher, "_get_client") as get_client:
                client = AsyncMock()
                client.get = mock_get
                get_client.return_value = client

                items = await fetcher.fetch_content("test")

        # Should return empty list when all scrapes fail
        assert items == []


# ---------------------------------------------------------------------------
# ADAPTERS registry test
# ---------------------------------------------------------------------------


class TestAdaptersRegistry:
    def test_all_adapters_registered(self):
        assert "hackernews" in ADAPTERS
        assert "reddit" in ADAPTERS
        assert "google" in ADAPTERS

    def test_adapter_types(self):
        assert ADAPTERS["hackernews"] is HackerNewsAdapter
        assert ADAPTERS["reddit"] is RedditAdapter
        assert ADAPTERS["google"] is GoogleTrendsAdapter

    def test_adapter_platform_names(self):
        for name, cls in ADAPTERS.items():
            instance = cls()
            assert instance.platform == name

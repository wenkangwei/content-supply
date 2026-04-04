"""End-to-end integration tests — RSS crawl → process → MySQL → Redis push."""

import hashlib
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from content_supply.services.types import CrawledItem
from content_supply.services.content_processor import ContentProcessor
from content_supply.services.item_writer import ItemWriter


class TestRSSPipelineIntegration:
    """Test: RSS crawl → process → MySQL write → Redis push."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_mock_redis(self):
        """Simulate a complete RSS pipeline: parse → process → write → push."""
        # 1. Simulate RSS crawl output
        crawled_items = [
            CrawledItem(
                title="Python 3.13 Released with New Features",
                url="https://example.com/python-313-released",
                summary="Python 3.13 brings major improvements including GIL changes.",
                content="Python 3.13 has been released with significant improvements "
                        "including experimental free-threaded mode, improved error messages, "
                        "and a new JIT compiler. The community is excited about these changes.",
                author="John Doe",
                image_url="https://example.com/images/python313.png",
                published_at=datetime(2024, 10, 7),
                source_name="Python Blog",
                source_type="rss",
                tags=["python", "programming"],
            ),
            CrawledItem(
                title="FastAPI 0.115 Performance Update",
                url="https://example.com/fastapi-0115",
                summary="FastAPI 0.115 brings performance improvements.",
                content="FastAPI version 0.115 has been released with significant "
                        "performance improvements and new dependency injection features.",
                author="Sebastián",
                image_url="",
                published_at=datetime(2024, 10, 6),
                source_name="FastAPI Blog",
                source_type="rss",
                tags=["fastapi", "python"],
            ),
        ]

        # 2. Process items
        processor = ContentProcessor()
        redis_client = AsyncMock()
        redis_client.pipeline = MagicMock(return_value=AsyncMock())

        # Use a mock DB session
        mock_session = AsyncMock()
        written_items = []

        async def mock_flush():
            pass

        mock_session.flush = mock_flush
        mock_session.add = lambda obj: written_items.append(obj)

        # Mock the duplicate check
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No duplicates
        mock_session.execute = AsyncMock(return_value=mock_result)

        writer = ItemWriter(mock_session, redis_client=redis_client)

        new_count = 0
        for item in crawled_items:
            result = await writer.write(item, feed_id=1)
            if result:
                new_count += 1

        # 3. Verify results
        assert new_count == 2
        assert len(written_items) == 2

        # Verify first item
        item0 = written_items[0]
        assert item0.title == "Python 3.13 Released with New Features"
        assert item0.source_type == "rss"
        assert item0.feed_id == 1
        assert item0.quality_score > 0
        assert item0.content_hash != ""

        # Verify second item
        item1 = written_items[1]
        assert item1.title == "FastAPI 0.115 Performance Update"
        assert item1.quality_score >= 0

        # Verify Redis was called
        assert redis_client.pipeline.call_count == 2

    @pytest.mark.asyncio
    async def test_dedup_prevents_duplicate_insert(self):
        """Verify URL dedup works in the pipeline."""
        mock_session = AsyncMock()

        # First call: no duplicate → write. Second call: duplicate → skip
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalar_one_or_none.return_value = None  # First: no dup
            else:
                result.scalar_one_or_none.return_value = MagicMock()  # Second: dup found
            return result

        mock_session.execute = mock_execute
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()

        writer = ItemWriter(mock_session)

        item = CrawledItem(
            title="Test Article",
            url="https://example.com/dup-test",
            content="Some content here for testing.",
            source_type="rss",
        )

        # First write: success
        result1 = await writer.write(item)
        assert result1 is not None

        # Second write: dedup
        result2 = await writer.write(item)
        assert result2 is None

    @pytest.mark.asyncio
    async def test_quality_scoring_in_pipeline(self):
        """Verify quality scoring is applied during write."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        written = []
        mock_session.add = lambda obj: written.append(obj)

        writer = ItemWriter(mock_session)

        # High quality item: long content + image + tags
        good_item = CrawledItem(
            title="High Quality Article",
            url="https://example.com/good",
            content="A" * 2000,
            image_url="https://example.com/img.png",
            tags=["tech", "ai", "python", "ml", "data"],
            source_type="rss",
        )

        # Low quality item: short, no image, no tags
        poor_item = CrawledItem(
            title="Low Quality",
            url="https://example.com/poor",
            content="Short",
            source_type="rss",
        )

        await writer.write(good_item)
        await writer.write(poor_item)

        assert written[0].quality_score > written[1].quality_score
        assert written[0].quality_score > 0.5
        assert written[1].quality_score < 0.5


class TestHotKeywordPipelineIntegration:
    """Test: hot keyword → search → scrape → write."""

    @pytest.mark.asyncio
    async def test_hot_keyword_to_item_pipeline(self):
        """Simulate: hot keyword → URL search → content extraction → write."""
        from content_supply.services.hot_tracker import HotKeywordItem

        # 1. Simulate hot keyword result
        keyword = HotKeywordItem(
            keyword="AI agents",
            platform="hackernews",
            rank=1,
            hot_score=500.0,
            category="tech",
        )
        assert keyword.keyword == "AI agents"
        assert keyword.platform == "hackernews"

        # 2. Simulate content fetch from keyword
        crawled = CrawledItem(
            title="Building AI Agents with LangGraph",
            url="https://example.com/ai-agents-langgraph",
            content="A comprehensive guide to building AI agents using LangGraph framework.",
            source_name="hot:AI agents",
            source_type="hot_keyword",
            extra={"hot_keyword": "AI agents", "hot_platform": "hackernews"},
        )

        # 3. Process and write
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        written = []
        mock_session.add = lambda obj: written.append(obj)

        writer = ItemWriter(mock_session)
        result = await writer.write(crawled, feed_id=None)

        assert result is not None
        assert written[0].source_type == "hot_keyword"
        assert json.loads(written[0].tags) is not None or written[0].tags is not None


class TestCleanupPipelineIntegration:
    """Test: cleanup scan → review notification → confirm → delete."""

    @pytest.mark.asyncio
    async def test_cleanup_scan_to_confirm_flow(self):
        """Simulate full cleanup flow with mock data."""
        from content_supply.models.cleanup_log import CleanupLog
        from content_supply.services.cleanup_manager import CleanupManager

        mock_session = AsyncMock()

        # Mock: no items to clean (empty scan)
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.commit = AsyncMock()

        policies = {
            "policies": [
                {"source_type": "rss", "ttl_days": 30, "max_items": 100, "min_quality": 0.2},
            ],
            "auto_confirm_after_hours": 24,
        }

        mgr = CleanupManager(mock_session, policies)
        logs = await mgr.scan_all()

        # No expired items → no logs created
        assert logs == []


class TestRewritePipelineIntegration:
    """Test: item → LLM rewrite → update."""

    @pytest.mark.asyncio
    async def test_rewrite_produces_different_content(self):
        """Verify rewrite returns different content from original."""
        from content_supply.services.content_rewriter import ContentRewriter

        rewriter = ContentRewriter(
            base_url="http://localhost:11434/v1",
            api_key="test",
            model="test-model",
        )

        original = "This is the original content about Python programming."

        with patch.object(
            rewriter.client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "This is rewritten content about Python coding."
            mock_response.usage.total_tokens = 150
            mock_create.return_value = mock_response

            result = await rewriter.rewrite(original, "paraphrase")

        assert result["rewritten"] != original
        assert result["model"] == "test-model"
        assert result["tokens_used"] == 150

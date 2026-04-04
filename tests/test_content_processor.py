"""Tests for ContentProcessor — hash, tags, quality, item-id."""

from datetime import datetime, timezone

import pytest

from content_supply.services.content_processor import ContentProcessor
from content_supply.services.types import CrawledItem


@pytest.fixture
def processor() -> ContentProcessor:
    return ContentProcessor()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(**overrides) -> CrawledItem:
    defaults = dict(
        title="Test Article Title",
        url="https://example.com/test-article",
        summary="A short summary.",
        content="Some body text.",
        author="Author Name",
        image_url="",
        published_at=None,
        source_name="Example",
        source_type="rss",
        tags=[],
        extra={},
    )
    defaults.update(overrides)
    return CrawledItem(**defaults)


# ---------------------------------------------------------------------------
# content_hash
# ---------------------------------------------------------------------------

class TestContentHash:
    def test_deterministic(self, processor):
        item = _make_item()
        h1 = processor.compute_content_hash(item)
        h2 = processor.compute_content_hash(item)
        assert h1 == h2
        assert isinstance(h1, str)
        assert len(h1) == 64  # SHA256 hex

    def test_different_content_different_hash(self, processor):
        item_a = _make_item(title="Alpha")
        item_b = _make_item(title="Beta")
        assert processor.compute_content_hash(item_a) != processor.compute_content_hash(item_b)

    def test_uses_first_1000_chars_of_content(self, processor):
        long_content = "x" * 2000
        item = _make_item(content=long_content)
        h1 = processor.compute_content_hash(item)

        # Change character at position 1001 — should NOT affect hash
        long_content2 = "x" * 1000 + "y" + "x" * 999
        item2 = _make_item(content=long_content2)
        h2 = processor.compute_content_hash(item2)
        assert h1 == h2

    def test_empty_content_falls_back_to_title(self, processor):
        item = _make_item(content="")
        h = processor.compute_content_hash(item)
        assert h  # should still produce a valid hash


# ---------------------------------------------------------------------------
# extract_tags
# ---------------------------------------------------------------------------

class TestExtractTags:
    def test_returns_list(self, processor):
        item = _make_item(title="Python programming")
        tags = processor.extract_tags(item)
        assert isinstance(tags, list)

    def test_extracts_english_keywords(self, processor):
        item = _make_item(
            title="Python programming language",
            content="Python is a great programming language for data science.",
        )
        tags = processor.extract_tags(item, max_tags=5)
        # "python" and "programming" should appear prominently
        assert "python" in tags
        assert "programming" in tags

    def test_respects_max_tags(self, processor):
        item = _make_item(
            title="alpha beta gamma delta epsilon zplota eta",
            content="alpha beta gamma delta epsilon zplota eta alpha beta",
        )
        tags = processor.extract_tags(item, max_tags=3)
        assert len(tags) <= 3

    def test_filters_stop_words(self, processor):
        item = _make_item(
            title="The quick brown fox",
            content="The fox is very quick and the brown fox jumps over the lazy dog",
        )
        tags = processor.extract_tags(item)
        # "the", "is", "over", "very" etc. should not appear
        assert "the" not in tags
        assert "is" not in tags

    def test_handles_cjk_characters(self, processor):
        item = _make_item(
            title="Python 编程 语言 教程",
            content="学习 Python 编程语言的最佳实践",
        )
        tags = processor.extract_tags(item)
        # Should contain some CJK characters
        assert any(ord(c[0]) > 0x4E00 for c in tags if c)

    def test_empty_item_returns_empty(self, processor):
        item = _make_item(title="", summary="", content="")
        tags = processor.extract_tags(item)
        assert tags == []


# ---------------------------------------------------------------------------
# score_quality
# ---------------------------------------------------------------------------

class TestScoreQuality:
    def test_range_zero_to_one(self, processor):
        item = _make_item(content="", image_url="", tags=[])
        score = processor.score_quality(item)
        assert 0.0 <= score <= 1.0

    def test_high_quality_item(self, processor):
        item = _make_item(
            content="word " * 800,  # 4000 chars -> capped at 1.0
            image_url="https://example.com/img.jpg",
            tags=["python", "ai", "ml", "data", "science"],
        )
        score = processor.score_quality(item)
        # content: 1.0*0.3=0.3, image: 0.2, source: 0.2, tags: 1.0*0.3=0.3 => 1.0
        assert score == 1.0

    def test_minimal_item(self, processor):
        item = _make_item(content="", image_url="", tags=[])
        score = processor.score_quality(item)
        # content: 0, image: 0, source: 0.2, tags: 0 => 0.2
        assert score == pytest.approx(0.2, abs=0.01)

    def test_score_increases_with_content_length(self, processor):
        short = _make_item(content="short")
        long = _make_item(content="x" * 3000)
        assert processor.score_quality(long) > processor.score_quality(short)

    def test_score_increases_with_image(self, processor):
        without_img = _make_item(image_url="")
        with_img = _make_item(image_url="https://example.com/img.jpg")
        assert processor.score_quality(with_img) > processor.score_quality(without_img)


# ---------------------------------------------------------------------------
# generate_item_id
# ---------------------------------------------------------------------------

class TestGenerateItemId:
    def test_deterministic(self, processor):
        item = _make_item()
        id1 = processor.generate_item_id(item)
        id2 = processor.generate_item_id(item)
        assert id1 == id2

    def test_length_16(self, processor):
        item = _make_item()
        item_id = processor.generate_item_id(item)
        assert len(item_id) == 16

    def test_different_urls_different_ids(self, processor):
        item_a = _make_item(url="https://example.com/a")
        item_b = _make_item(url="https://example.com/b")
        assert processor.generate_item_id(item_a) != processor.generate_item_id(item_b)

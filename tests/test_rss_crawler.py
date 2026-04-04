"""Tests for RSSCrawler and CrawledItem."""

from datetime import datetime

import pytest

from content_supply.services.rss_crawler import CrawledItem, RSSCrawler

# ---------------------------------------------------------------------------
# Sample RSS/Atom XML fixtures
# ---------------------------------------------------------------------------

SAMPLE_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>A test RSS feed</description>
    <item>
      <title>First Post</title>
      <link>https://example.com/first</link>
      <description>Summary of the first post</description>
      <author>alice</author>
      <pubDate>Thu, 01 Jan 2024 00:00:00 GMT</pubDate>
      <media:content url="https://example.com/img1.jpg" medium="image" type="image/jpeg"/>
      <category>Tech</category>
      <category>Python</category>
    </item>
    <item>
      <title>Second Post</title>
      <link>https://example.com/second</link>
      <description>Summary of the second post</description>
      <author>bob</author>
      <pubDate>Fri, 02 Feb 2024 12:30:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

SAMPLE_ATOM = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <link href="https://example.com"/>
  <entry>
    <title>Atom Entry</title>
    <link href="https://example.com/atom1"/>
    <summary>Atom summary</summary>
    <author><name>charlie</name></author>
    <updated>2024-03-15T10:00:00Z</updated>
  </entry>
</feed>
"""

EMPTY_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
    <link>https://example.com</link>
  </channel>
</rss>
"""

INVALID_XML = "this is not xml at all"

RSS_MISSING_FIELDS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Partial Feed</title>
    <item>
      <title>No link item</title>
    </item>
    <item>
      <link>https://example.com/no-title</link>
    </item>
    <item>
      <title>Valid Entry</title>
      <link>https://example.com/valid</link>
      <description>Has all required fields</description>
    </item>
  </channel>
</rss>
"""


# ---------------------------------------------------------------------------
# CrawledItem dataclass tests
# ---------------------------------------------------------------------------


class TestCrawledItem:
    def test_defaults(self):
        item = CrawledItem(title="t", url="u")
        assert item.title == "t"
        assert item.url == "u"
        assert item.summary == ""
        assert item.content == ""
        assert item.author == ""
        assert item.image_url == ""
        assert item.published_at is None
        assert item.source_name == ""
        assert item.tags == []
        assert item.extra == {}

    def test_full_construction(self):
        now = datetime(2024, 1, 1)
        item = CrawledItem(
            title="Title",
            url="https://example.com",
            summary="sum",
            content="body",
            author="auth",
            image_url="https://img.png",
            published_at=now,
            source_name="src",
            tags=["a", "b"],
            extra={"key": "val"},
        )
        assert item.published_at == now
        assert item.tags == ["a", "b"]
        assert item.extra["key"] == "val"

    def test_tags_isolation(self):
        """Each instance should get its own default list."""
        a = CrawledItem(title="a", url="a")
        b = CrawledItem(title="b", url="b")
        a.tags.append("x")
        assert b.tags == []


# ---------------------------------------------------------------------------
# RSSCrawler tests
# ---------------------------------------------------------------------------


@pytest.fixture
def crawler():
    return RSSCrawler()


class TestRSSCrawlerFetch:
    @pytest.mark.asyncio
    async def test_parse_rss(self, crawler):
        items = await crawler.fetch(SAMPLE_RSS, source_name="test-rss")
        assert len(items) == 2

        first = items[0]
        assert first.title == "First Post"
        assert first.url == "https://example.com/first"
        assert "Summary of the first" in first.summary
        assert first.author == "alice"
        assert first.image_url == "https://example.com/img1.jpg"
        assert first.source_name == "test-rss"
        assert "Tech" in first.tags
        assert "Python" in first.tags
        assert first.published_at is not None
        assert first.published_at.year == 2024

    @pytest.mark.asyncio
    async def test_parse_atom(self, crawler):
        items = await crawler.fetch(SAMPLE_ATOM, source_name="test-atom")
        assert len(items) == 1
        entry = items[0]
        assert entry.title == "Atom Entry"
        assert entry.url == "https://example.com/atom1"
        assert entry.author == "charlie"

    @pytest.mark.asyncio
    async def test_empty_feed(self, crawler):
        items = await crawler.fetch(EMPTY_RSS)
        assert items == []

    @pytest.mark.asyncio
    async def test_invalid_xml(self, crawler):
        # feedparser will still parse it (returns empty entries with bozo)
        items = await crawler.fetch(INVALID_XML)
        assert isinstance(items, list)

    @pytest.mark.asyncio
    async def test_partial_entries_skipped(self, crawler):
        """Entries missing required title or link should be dropped."""
        items = await crawler.fetch(RSS_MISSING_FIELDS)
        assert len(items) == 1
        assert items[0].title == "Valid Entry"
        assert items[0].url == "https://example.com/valid"


class TestParseEntry:
    """Unit tests for the internal _parse_entry method."""

    def test_entry_with_media_content(self, crawler):
        import feedparser

        feed = feedparser.parse(SAMPLE_RSS)
        entry = feed.entries[0]
        result = crawler._parse_entry(entry, "src")
        assert result is not None
        assert result.image_url == "https://example.com/img1.jpg"

    def test_entry_without_image(self, crawler):
        import feedparser

        feed = feedparser.parse(SAMPLE_RSS)
        entry = feed.entries[1]
        result = crawler._parse_entry(entry, "src")
        assert result is not None
        assert result.image_url == ""

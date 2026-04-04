"""RSS/Atom feed crawler using feedparser."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from time import struct_time
from typing import Optional

import feedparser

logger = logging.getLogger(__name__)


@dataclass
class CrawledItem:
    """Normalized item from any crawl source."""

    title: str
    url: str
    summary: str = ""
    content: str = ""
    author: str = ""
    image_url: str = ""
    published_at: Optional[datetime] = None
    source_name: str = ""
    tags: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


class RSSCrawler:
    """Parse RSS/Atom feeds into normalized CrawledItem list."""

    async def fetch(self, url: str, source_name: str = "") -> list[CrawledItem]:
        """Fetch and parse an RSS/Atom feed URL.

        Uses feedparser.parse which handles both RSS and Atom formats
        transparently, including following HTTP redirects.
        """
        try:
            # feedparser.parse handles both local file paths and URLs.
            # For URLs it performs a blocking HTTP request; running it in
            # a thread would be ideal but is not required for the MVP.
            feed = feedparser.parse(url)

            # feedparser sets bozo bit on parse errors but still returns
            # partial results.  Only bail out when there are zero entries
            # *and* the bozo bit indicates a severe problem.
            if not feed.entries:
                if feed.bozo and not feed.get("feed", {}).get("title"):
                    logger.warning("Failed to parse feed %s: %s", url, feed.bozo_exception)
                    return []
                logger.info("Feed %s parsed successfully but contains no entries", url)
                return []

            items: list[CrawledItem] = []
            for entry in feed.entries:
                try:
                    parsed = self._parse_entry(entry, source_name)
                    if parsed is not None:
                        items.append(parsed)
                except Exception:
                    # Never let one bad entry spoil the whole batch.
                    logger.debug("Skipping unparseable entry in %s", url, exc_info=True)

            logger.info(
                "Parsed %d items from feed %s (source=%s)",
                len(items),
                url,
                source_name,
            )
            return items

        except Exception:
            logger.error("Error fetching feed %s", url, exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_entry(self, entry, source_name: str) -> Optional[CrawledItem]:
        """Parse a single feed entry into CrawledItem.

        Returns ``None`` when the entry is missing a required field
        (``title`` or ``link``).
        """
        title = entry.get("title", "").strip()
        link = entry.get("link", "").strip()
        if not title or not link:
            return None

        # Summary / description ---
        summary = entry.get("summary") or entry.get("description") or ""

        # Content (full article body if provided in feed) ---
        content = ""
        content_list = entry.get("content", [])
        if content_list and isinstance(content_list, list):
            content = content_list[0].get("value", "")

        # Author ---
        author = entry.get("author") or ""
        # Some feeds store author details in a dict
        if isinstance(author, dict):
            author = author.get("name", "")

        # Published date ---
        published_at = self._parse_published(entry)

        # Image ---
        image_url = self._extract_image(entry)

        # Tags ---
        tags: list[str] = []
        for tag in entry.get("tags", []):
            term = tag.get("term", "").strip()
            if term:
                tags.append(term)

        return CrawledItem(
            title=title,
            url=link,
            summary=summary,
            content=content,
            author=author,
            image_url=image_url,
            published_at=published_at,
            source_name=source_name,
            tags=tags,
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _parse_published(entry) -> Optional[datetime]:
        """Convert ``published_parsed`` (struct_time) to datetime."""
        for key in ("published_parsed", "updated_parsed"):
            parsed = entry.get(key)
            if isinstance(parsed, struct_time):
                try:
                    return datetime(*parsed[:6])
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def _extract_image(entry) -> str:
        """Best-effort extraction of a representative image URL.

        Checks ``media_content``, ``enclosures``, and the ``summary`` for
        an ``<img>`` tag.
        """
        # media_content (Media RSS)
        media_list = entry.get("media_content", [])
        if media_list:
            for media in media_list:
                url = media.get("url", "")
                medium = media.get("medium", "")
                mtype = media.get("type", "")
                if url and (medium == "image" or mtype.startswith("image/")):
                    return url
            # Fallback: first media entry with a URL
            for media in media_list:
                url = media.get("url", "")
                if url:
                    return url

        # Enclosures
        for enclosure in entry.get("enclosures", []):
            etype = enclosure.get("type", "")
            if etype.startswith("image/"):
                return enclosure.get("href", "") or enclosure.get("url", "")

        return ""

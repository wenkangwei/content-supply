"""Shared data types for the content pipeline."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


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
    source_type: str = "rss"
    tags: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

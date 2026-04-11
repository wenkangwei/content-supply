"""Task Pydantic schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class CrawlTaskResponse(BaseModel):
    id: int
    feed_id: Optional[int] = None
    hot_keyword_id: Optional[int] = None
    url: str
    task_type: str
    status: str
    items_found: int = 0
    items_new: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlUrlRequest(BaseModel):
    url: str
    category: str = ""


class CrawledContentResponse(BaseModel):
    """Detailed response for /crawl/url including extracted content."""
    task: CrawlTaskResponse
    item: Optional[dict[str, Any]] = None


class JimengArtwork(BaseModel):
    """Single Jimeng artwork item."""
    id: str
    title: str = ""
    description: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    cover_url: str = ""
    cover_url_map: dict[str, str] = {}
    aspect_ratio: float = 0.0
    author: str = ""
    width: int = 0
    height: int = 0
    format: str = ""
    seed: str = ""
    usage_num: int = 0
    favorite_num: int = 0
    create_time: Optional[int] = None
    detail_url: str = ""
    image_valid: bool = True


class JimengCrawlResponse(BaseModel):
    """Response for /crawl/jimeng endpoint."""
    task: CrawlTaskResponse
    items: list[JimengArtwork] = []

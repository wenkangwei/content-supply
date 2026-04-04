"""Task Pydantic schemas."""

from datetime import datetime
from typing import Optional

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

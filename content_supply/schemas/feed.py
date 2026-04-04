"""Feed Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl


class FeedCreate(BaseModel):
    name: str
    url: str
    source_type: str = "rss"
    category: str = ""
    poll_interval: int = 1800


class FeedUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    category: Optional[str] = None
    poll_interval: Optional[int] = None
    status: Optional[str] = None


class FeedResponse(BaseModel):
    id: int
    name: str
    url: str
    source_type: str
    category: str
    poll_interval: int
    last_fetched_at: Optional[datetime] = None
    last_error: Optional[str] = None
    error_count: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

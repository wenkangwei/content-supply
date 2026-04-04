"""Item Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ItemResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    url: str
    image_url: Optional[str] = None
    author: Optional[str] = None
    source_name: Optional[str] = None
    source_type: str
    content_type: str
    tags: Optional[str] = None
    category: Optional[str] = None
    quality_score: float = 0.0
    is_rewritten: bool = False
    exposure_count: int = 0
    click_count: int = 0
    status: str
    published_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ItemListParams(BaseModel):
    page: int = 1
    page_size: int = 20
    source_type: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None


class ItemSearchParams(BaseModel):
    query: str
    page: int = 1
    page_size: int = 20
    source_type: Optional[str] = None

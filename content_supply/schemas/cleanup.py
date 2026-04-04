"""Cleanup Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CleanupPolicyResponse(BaseModel):
    source_type: str
    ttl_days: int
    max_items: int
    min_quality: float
    cold_start_ttl_days: Optional[int] = None


class CleanupLogResponse(BaseModel):
    id: int
    policy: str
    source_type: str
    status: str
    items_scanned: int = 0
    items_to_delete: int = 0
    items_deleted: int = 0
    space_freed_mb: float = 0.0
    notification_sent: bool = False
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    auto_confirm_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CleanupReviewRequest(BaseModel):
    reviewer: str = "system"

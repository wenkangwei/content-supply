"""CleanupLog model — cleanup operation audit with review workflow."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from content_supply.models.base import Base


class CleanupLog(Base):
    __tablename__ = "cs_cleanup_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    policy: Mapped[str] = mapped_column(String(50), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending_review", "approved", "rejected", "executing", "done", "expired",
            name="cleanup_status",
        ),
        default="pending_review",
    )
    items_scanned: Mapped[int] = mapped_column(Integer, default=0)
    items_to_delete: Mapped[int] = mapped_column(Integer, default=0)
    items_deleted: Mapped[int] = mapped_column(Integer, default=0)
    space_freed_mb: Mapped[float] = mapped_column(Float, default=0.0)
    pending_item_ids: Mapped[str | None] = mapped_column(Text("json"), nullable=True)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    auto_confirm_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    details: Mapped[str | None] = mapped_column(Text("json"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

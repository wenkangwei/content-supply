"""CrawlTask model — crawl job tracking."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from content_supply.models.base import Base


class CrawlTask(Base):
    __tablename__ = "cs_crawl_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feed_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hot_keyword_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    task_type: Mapped[str] = mapped_column(
        Enum("rss", "web", "manual", "hot_keyword", name="task_type"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "done", "failed", name="task_status"),
        default="pending",
    )
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

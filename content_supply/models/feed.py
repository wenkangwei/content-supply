"""Feed model — RSS/Atom source management."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from content_supply.models.base import Base


class Feed(Base):
    __tablename__ = "cs_feeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(
        Enum("rss", "atom", "web", "hot_search", name="feed_source_type"),
        default="rss",
    )
    category: Mapped[str] = mapped_column(String(100), default="")
    poll_interval: Mapped[int] = mapped_column(Integer, default=1800)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        Enum("active", "paused", "error", name="feed_status"),
        default="active",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

"""Item model — content pool (core table read by recommendation system)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from content_supply.models.base import Base


class Item(Base):
    __tablename__ = "cs_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(768), unique=True, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(
        Enum("rss", "web", "hot_keyword", "manual", "jimeng", name="item_source_type"),
        default="rss",
    )
    feed_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hot_keyword_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str] = mapped_column(
        Enum("article", "video", "post", name="item_content_type"),
        default="article",
    )
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_rewritten: Mapped[bool] = mapped_column(Boolean, default=False)
    rewrite_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exposure_count: Mapped[int] = mapped_column(Integer, default=0)
    click_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        Enum("draft", "published", "archived", name="item_status"),
        default="published",
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

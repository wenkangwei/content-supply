"""RewriteTask model — LLM content rewriting tracking."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from content_supply.models.base import Base


class RewriteTask(Base):
    __tablename__ = "cs_rewrite_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rewrite_type: Mapped[str] = mapped_column(
        Enum("paraphrase", "summarize", "expand", name="rewrite_type"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "done", "failed", name="rewrite_status"),
        default="pending",
    )
    original_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

"""Feed manager — CRUD + status management."""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from content_supply.models.feed import Feed
from content_supply.schemas.feed import FeedCreate, FeedUpdate


class FeedManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_feeds(
        self,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Feed]:
        stmt = select(Feed).order_by(Feed.created_at.desc())
        if status:
            stmt = stmt.where(Feed.status == status)
        if source_type:
            stmt = stmt.where(Feed.source_type == source_type)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_feed(self, feed_id: int) -> Optional[Feed]:
        result = await self.session.execute(select(Feed).where(Feed.id == feed_id))
        return result.scalar_one_or_none()

    async def create_feed(self, data: FeedCreate) -> Feed:
        feed = Feed(
            name=data.name,
            url=data.url,
            source_type=data.source_type,
            category=data.category,
            poll_interval=data.poll_interval,
        )
        self.session.add(feed)
        await self.session.flush()
        return feed

    async def update_feed(self, feed_id: int, data: FeedUpdate) -> Optional[Feed]:
        feed = await self.get_feed(feed_id)
        if not feed:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            if hasattr(feed, k) and v is not None:
                setattr(feed, k, v)
        await self.session.flush()
        return feed

    async def delete_feed(self, feed_id: int) -> bool:
        feed = await self.get_feed(feed_id)
        if not feed:
            return False
        await self.session.delete(feed)
        await self.session.flush()
        return True

    async def toggle_feed(self, feed_id: int) -> Optional[Feed]:
        feed = await self.get_feed(feed_id)
        if not feed:
            return None
        feed.status = "paused" if feed.status == "active" else "active"
        feed.error_count = 0
        feed.last_error = None
        await self.session.flush()
        return feed

    async def get_active_feeds(self) -> list[Feed]:
        result = await self.session.execute(
            select(Feed).where(Feed.status == "active").order_by(Feed.id)
        )
        return list(result.scalars().all())

    async def update_fetch_status(
        self,
        feed_id: int,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        feed = await self.get_feed(feed_id)
        if not feed:
            return
        feed.last_fetched_at = datetime.now()
        if success:
            feed.error_count = 0
            feed.last_error = None
            if feed.status == "error":
                feed.status = "active"
        else:
            feed.error_count = (feed.error_count or 0) + 1
            feed.last_error = error
            if feed.error_count >= 5:
                feed.status = "error"

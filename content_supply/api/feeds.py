"""Feed CRUD API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from content_supply.api.deps import get_db
from content_supply.schemas.feed import FeedCreate, FeedResponse, FeedUpdate
from content_supply.services.feed_manager import FeedManager

router = APIRouter()


@router.get("/feeds", response_model=list[FeedResponse])
async def list_feeds(
    status: Optional[str] = None,
    source_type: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    mgr = FeedManager(db)
    feeds = await mgr.list_feeds(status=status, source_type=source_type, limit=limit, offset=offset)
    return feeds


@router.post("/feeds", response_model=FeedResponse, status_code=201)
async def create_feed(data: FeedCreate, db: AsyncSession = Depends(get_db)):
    mgr = FeedManager(db)
    feed = await mgr.create_feed(data)
    await db.commit()
    return feed


@router.get("/feeds/{feed_id}", response_model=FeedResponse)
async def get_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    mgr = FeedManager(db)
    feed = await mgr.get_feed(feed_id)
    if not feed:
        raise HTTPException(404, "Feed not found")
    return feed


@router.put("/feeds/{feed_id}", response_model=FeedResponse)
async def update_feed(feed_id: int, data: FeedUpdate, db: AsyncSession = Depends(get_db)):
    mgr = FeedManager(db)
    feed = await mgr.update_feed(feed_id, data)
    if not feed:
        raise HTTPException(404, "Feed not found")
    await db.commit()
    return feed


@router.delete("/feeds/{feed_id}", status_code=204)
async def delete_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    mgr = FeedManager(db)
    deleted = await mgr.delete_feed(feed_id)
    if not deleted:
        raise HTTPException(404, "Feed not found")
    await db.commit()


@router.post("/feeds/{feed_id}/toggle", response_model=FeedResponse)
async def toggle_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    mgr = FeedManager(db)
    feed = await mgr.toggle_feed(feed_id)
    if not feed:
        raise HTTPException(404, "Feed not found")
    await db.commit()
    return feed

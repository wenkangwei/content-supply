"""Hot keyword API — view trending keywords and trigger fetch."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from content_supply.api.deps import get_db
from content_supply.models.hot_keyword import HotKeyword

router = APIRouter()


@router.get("/hot/keywords")
async def list_hot_keywords(
    platform: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List hot keywords, optionally filtered by platform."""
    stmt = select(HotKeyword).order_by(HotKeyword.fetched_at.desc())
    if platform:
        stmt = stmt.where(HotKeyword.platform == platform)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    keywords = list(result.scalars().all())
    return [
        {
            "id": kw.id,
            "keyword": kw.keyword,
            "platform": kw.platform,
            "rank": kw.rank,
            "hot_score": kw.hot_score,
            "category": kw.category,
            "fetched_at": str(kw.fetched_at),
            "content_fetched": kw.content_fetched,
        }
        for kw in keywords
    ]


@router.post("/hot/trigger")
async def trigger_hot_fetch(
    platforms: Optional[list[str]] = None, db: AsyncSession = Depends(get_db)
):
    """Manually trigger hot keyword fetch for specified platforms."""
    from content_supply.services.hot_tracker import HotTracker
    from datetime import datetime

    tracker = HotTracker()
    targets = platforms or ["hackernews", "reddit", "google"]
    results = await tracker.fetch_all(platforms=targets)

    total_new = 0
    for platform, keywords in results.items():
        for kw in keywords:
            # Check if recently fetched
            exists = await db.execute(
                select(HotKeyword).where(
                    HotKeyword.keyword == kw.keyword,
                    HotKeyword.platform == kw.platform,
                    HotKeyword.fetched_at > datetime.now().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ),
                )
            )
            if exists.scalar_one_or_none():
                continue
            hk = HotKeyword(
                keyword=kw.keyword,
                platform=kw.platform,
                rank=kw.rank,
                hot_score=kw.hot_score,
                category=kw.category,
            )
            db.add(hk)
            total_new += 1

    await db.commit()
    return {
        "status": "done",
        "platforms_fetched": list(results.keys()),
        "keywords_new": total_new,
        "keywords_total": sum(len(kws) for kws in results.values()),
    }

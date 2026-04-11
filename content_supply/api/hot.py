"""Hot keyword API — view trending keywords, trigger fetch, and fetch related content."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func as sa_func
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


@router.post("/hot/{keyword_id}/fetch-content")
async def fetch_content_for_keyword(
    keyword_id: int,
    max_results: int = Query(default=5, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Search and fetch related articles for a specific hot keyword."""
    from content_supply.services.hot_content_fetcher import HotContentFetcher
    from content_supply.services.item_writer import ItemWriter
    from content_supply.models.crawl_task import CrawlTask
    from datetime import datetime

    # Load keyword
    result = await db.execute(select(HotKeyword).where(HotKeyword.id == keyword_id))
    kw = result.scalar_one_or_none()
    if not kw:
        raise HTTPException(404, f"Hot keyword #{keyword_id} not found")

    if kw.content_fetched:
        return {
            "status": "skipped",
            "keyword": kw.keyword,
            "message": "Content already fetched for this keyword",
        }

    # Create crawl task
    task = CrawlTask(
        url=f"hot:{kw.keyword}",
        task_type="hot_keyword",
        status="running",
        hot_keyword_id=kw.id,
    )
    db.add(task)
    await db.flush()

    try:
        fetcher = HotContentFetcher()
        items = await fetcher.fetch_content(
            keyword=kw.keyword,
            platform=kw.platform,
            max_results=max_results,
        )
        await fetcher.close()

        task.items_found = len(items)

        writer = ItemWriter(db)
        count = 0
        for item in items:
            result = await writer.write(item)
            if result:
                count += 1

        task.items_new = count
        task.status = "done"

        # Mark keyword as fetched
        kw.content_fetched = True
        kw.status = "done"

    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)

    task.finished_at = datetime.now()
    await db.commit()

    return {
        "status": task.status,
        "keyword": kw.keyword,
        "platform": kw.platform,
        "items_found": task.items_found,
        "items_new": task.items_new,
        "error_message": task.error_message,
    }


@router.post("/hot/fetch-content")
async def fetch_content_batch(
    max_keywords: int = Query(default=10, le=50),
    max_results_per_keyword: int = Query(default=3, le=10),
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Batch fetch related articles for all unfetched hot keywords.

    Processes keywords ordered by hot_score descending (most popular first).
    """
    from content_supply.services.hot_content_fetcher import HotContentFetcher
    from content_supply.services.item_writer import ItemWriter
    from content_supply.models.crawl_task import CrawlTask
    from datetime import datetime
    import asyncio

    # Find unfetched keywords
    stmt = (
        select(HotKeyword)
        .where(HotKeyword.content_fetched == False)
        .order_by(HotKeyword.hot_score.desc())
        .limit(max_keywords)
    )
    if platform:
        stmt = stmt.where(HotKeyword.platform == platform)

    result = await db.execute(stmt)
    keywords = list(result.scalars().all())

    if not keywords:
        return {
            "status": "done",
            "keywords_processed": 0,
            "message": "No unfetched keywords found",
        }

    fetcher = HotContentFetcher()
    writer = ItemWriter(db)
    total_found = 0
    total_new = 0
    processed = 0

    for kw in keywords:
        try:
            kw.status = "processing"

            items = await fetcher.fetch_content(
                keyword=kw.keyword,
                platform=kw.platform,
                max_results=max_results_per_keyword,
            )
            total_found += len(items)

            count = 0
            for item in items:
                result = await writer.write(item)
                if result:
                    count += 1
            total_new += count

            kw.content_fetched = True
            kw.status = "done"
            processed += 1

        except Exception as e:
            kw.status = "failed"
            import logging
            logging.getLogger(__name__).warning(
                "Hot content fetch failed for '%s': %s", kw.keyword, e
            )

    await fetcher.close()
    await db.commit()

    return {
        "status": "done",
        "keywords_processed": processed,
        "total_keywords": len(keywords),
        "items_found": total_found,
        "items_new": total_new,
    }

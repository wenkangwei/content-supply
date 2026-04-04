"""Crawl API — manual trigger for feed crawl and URL scraping."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from content_supply.api.deps import get_db
from content_supply.models.crawl_task import CrawlTask
from content_supply.schemas.task import CrawlTaskResponse, CrawlUrlRequest

router = APIRouter()


@router.post("/crawl/feed/{feed_id}", response_model=CrawlTaskResponse)
async def crawl_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    """Manually trigger crawl for a specific feed."""
    from content_supply.services.feed_manager import FeedManager
    from content_supply.services.rss_crawler import RSSCrawler
    from content_supply.services.item_writer import ItemWriter
    from datetime import datetime

    mgr = FeedManager(db)
    feed = await mgr.get_feed(feed_id)
    if not feed:
        raise HTTPException(404, "Feed not found")

    task = CrawlTask(feed_id=feed_id, url=feed.url, task_type="rss", status="running")
    db.add(task)
    await db.flush()

    try:
        crawler = RSSCrawler()
        items = await crawler.fetch(feed.url, source_name=feed.name)
        task.items_found = len(items)

        writer = ItemWriter(db)
        count = 0
        for item in items:
            result = await writer.write(item, feed_id=feed_id)
            if result:
                count += 1

        task.items_new = count
        task.status = "done"
        await mgr.update_fetch_status(feed_id, True)
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        await mgr.update_fetch_status(feed_id, False, error=str(e))

    task.finished_at = datetime.now()
    await db.commit()
    return task


@router.post("/crawl/url", response_model=CrawlTaskResponse)
async def crawl_url(data: CrawlUrlRequest, db: AsyncSession = Depends(get_db)):
    """Manually scrape a single URL."""
    from content_supply.services.web_scraper import WebScraper
    from content_supply.services.item_writer import ItemWriter
    from datetime import datetime

    task = CrawlTask(url=data.url, task_type="manual", status="running")
    db.add(task)
    await db.flush()

    try:
        scraper = WebScraper()
        item = await scraper.scrape(data.url)
        if not item:
            task.status = "failed"
            task.error_message = "Failed to extract content from URL"
            task.finished_at = datetime.now()
            await db.commit()
            return task

        item.source_type = "manual"
        item.extra["category"] = data.category

        writer = ItemWriter(db)
        result = await writer.write(item)
        task.items_found = 1
        task.items_new = 1 if result else 0
        task.status = "done"
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)

    task.finished_at = datetime.now()
    await db.commit()
    return task


@router.get("/tasks", response_model=list[CrawlTaskResponse])
async def list_tasks(
    task_type: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List crawl tasks."""
    stmt = select(CrawlTask).order_by(CrawlTask.created_at.desc())
    if task_type:
        stmt = stmt.where(CrawlTask.task_type == task_type)
    if status:
        stmt = stmt.where(CrawlTask.status == status)
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())

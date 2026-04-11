"""Crawl API — manual trigger for feed crawl and URL scraping."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import yaml

from content_supply.api.deps import get_db
from content_supply.config import CONFIGS_DIR, load_app_config
from content_supply.models.crawl_task import CrawlTask
from content_supply.schemas.task import (
    CrawledContentResponse,
    CrawlTaskResponse,
    CrawlUrlRequest,
    JimengArtwork,
    JimengCrawlResponse,
)

router = APIRouter()


@router.get("/crawl/web-sources")
async def list_web_sources():
    """List all configured web sources and their status."""
    config = load_app_config()
    try:
        ws_config = yaml.safe_load(open(CONFIGS_DIR / "web_sources.yaml"))
        sources = ws_config.get("web_sources", [])
    except FileNotFoundError:
        sources = []
    return {
        "sources": [
            {
                "name": s.get("name", ""),
                "url": s.get("url", ""),
                "category": s.get("category", ""),
                "poll_interval": s.get("poll_interval", 0),
                "max_articles": s.get("max_articles", 10),
                "enabled": s.get("enabled", False),
            }
            for s in sources
        ],
        "total": len(sources),
    }


@router.post("/crawl/web-source/{source_name}", response_model=CrawlTaskResponse)
async def crawl_web_source(source_name: str, db: AsyncSession = Depends(get_db)):
    """Manually trigger crawl for a specific web source by name."""
    config = load_app_config()
    try:
        ws_config = yaml.safe_load(open(CONFIGS_DIR / "web_sources.yaml"))
        sources = ws_config.get("web_sources", [])
    except FileNotFoundError:
        raise HTTPException(404, "web_sources.yaml not found")

    source = None
    for s in sources:
        if s["name"] == source_name:
            source = s
            break
    if not source:
        raise HTTPException(404, f"Web source '{source_name}' not found in config")

    from content_supply.services.web_source_crawler import WebSourceCrawler
    from content_supply.services.item_writer import ItemWriter

    task = CrawlTask(
        url=source["url"],
        task_type="web",
        status="running",
    )
    db.add(task)
    await db.flush()

    try:
        crawler = WebSourceCrawler()
        items = await crawler.crawl_source(source)
        task.items_found = len(items)

        writer = ItemWriter(db)
        count = 0
        for item in items:
            result = await writer.write(item)
            if result:
                count += 1

        task.items_new = count
        task.status = "done"
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)

    task.finished_at = datetime.now()
    await db.commit()
    return task


@router.post("/crawl/feed/{feed_id}", response_model=CrawlTaskResponse)
async def crawl_feed(feed_id: int, db: AsyncSession = Depends(get_db)):
    """Manually trigger crawl for a specific feed."""
    from content_supply.services.feed_manager import FeedManager
    from content_supply.services.item_writer import ItemWriter
    from content_supply.services.rss_crawler import RSSCrawler

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


@router.post("/crawl/url", response_model=CrawledContentResponse)
async def crawl_url(data: CrawlUrlRequest, db: AsyncSession = Depends(get_db)):
    """Manually scrape a single URL and return extracted content."""
    from content_supply.services.item_writer import ItemWriter
    from content_supply.services.web_scraper import ScrapeError, WebScraper

    task = CrawlTask(url=data.url, task_type="manual", status="running")
    db.add(task)
    await db.flush()

    item_dict = None

    try:
        scraper = WebScraper()
        crawled = await scraper.scrape(data.url, check_robots=False)

        if not crawled:
            task.status = "failed"
            task.error_message = "Failed to extract content from URL"
            task.finished_at = datetime.now()
            await db.commit()
            return CrawledContentResponse(task=task, item=None)

        crawled.source_type = "manual"
        crawled.extra["category"] = data.category

        writer = ItemWriter(db)
        result = await writer.write(crawled)
        task.items_found = 1
        task.items_new = 1 if result else 0
        task.status = "done"

        # Build content dict from the CrawledItem for immediate display
        item_dict = {
            "title": crawled.title,
            "url": crawled.url,
            "summary": crawled.summary,
            "content": crawled.content,
            "author": crawled.author,
            "image_url": crawled.image_url,
            "published_at": crawled.published_at.isoformat() if crawled.published_at else None,
            "source_type": crawled.source_type,
            "tags": crawled.tags,
        }

    except ScrapeError as e:
        task.status = "failed"
        task.error_message = f"不支持抓取: {e.reason}"
        item_dict = None
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        item_dict = None

    task.finished_at = datetime.now()
    await db.commit()
    return CrawledContentResponse(task=task, item=item_dict)


@router.post("/crawl/jimeng", response_model=JimengCrawlResponse)
async def crawl_jimeng(db: AsyncSession = Depends(get_db)):
    """Scrape Jimeng (即梦) AI artwork gallery.

    Fetches the homepage, extracts all artwork items with their
    prompts, images, and metadata. Validates image URLs accessibility.
    """
    import httpx

    from content_supply.services.web_scraper import WebScraper

    task = CrawlTask(
        url="https://jimeng.jianying.com/ai-tool/home",
        task_type="jimeng",
        status="running",
    )
    db.add(task)
    await db.flush()

    artworks: list[JimengArtwork] = []

    try:
        scraper = WebScraper()
        # Fetch the homepage HTML directly
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            },
        ) as client:
            response = await client.get("https://jimeng.jianying.com/ai-tool/home")
            response.raise_for_status()
            html = response.text

        # Parse items using the Jimeng extractor
        title, content, author, published_at = scraper._extract_jimeng(html, "https://jimeng.jianying.com/ai-tool/home")
        raw_items = scraper._jimeng_items

        if not raw_items:
            task.status = "failed"
            task.error_message = "未获取到即梦作品数据"
            task.finished_at = datetime.now()
            await db.commit()
            return JimengCrawlResponse(task=task, items=[])

        # Validate image URLs — batch check
        all_cover_urls = [item["cover_url"] for item in raw_items if item.get("cover_url")]
        valid_urls = set(await scraper._validate_image_urls(all_cover_urls))

        for item_data in raw_items:
            cover = item_data.get("cover_url", "")
            image_valid = cover in valid_urls if cover else False

            artworks.append(JimengArtwork(
                id=item_data.get("id", ""),
                title=item_data.get("title", ""),
                description=item_data.get("description", ""),
                prompt=item_data.get("prompt", ""),
                negative_prompt=item_data.get("negative_prompt", ""),
                cover_url=cover,
                cover_url_map=item_data.get("cover_url_map", {}),
                aspect_ratio=item_data.get("aspect_ratio", 0),
                author=item_data.get("author", ""),
                width=item_data.get("width", 0),
                height=item_data.get("height", 0),
                format=item_data.get("format", ""),
                seed=item_data.get("seed", ""),
                usage_num=item_data.get("usage_num", 0),
                favorite_num=item_data.get("favorite_num", 0),
                create_time=item_data.get("create_time"),
                detail_url=item_data.get("detail_url", ""),
                image_valid=image_valid,
            ))

        # Filter: only include items with valid images
        valid_artworks = [a for a in artworks if a.image_valid]
        task.items_found = len(raw_items)
        task.items_new = len(valid_artworks)
        task.status = "done"

        # Write valid items to DB
        from content_supply.services.item_writer import ItemWriter

        writer = ItemWriter(db)
        from content_supply.services.rss_crawler import CrawledItem

        for artwork in valid_artworks:
            crawled = CrawledItem(
                title=artwork.title or f"即梦作品 {artwork.id[:8]}",
                url=artwork.detail_url,
                summary=artwork.description or artwork.prompt[:200],
                content=artwork.prompt,
                author=artwork.author,
                image_url=artwork.cover_url,
                source_name="即梦AI",
                source_type="jimeng",
                tags=["AI绘画", "即梦", "Jimeng"],
            )
            await writer.write(crawled)

    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)

    task.finished_at = datetime.now()
    await db.commit()
    return JimengCrawlResponse(task=task, items=artworks)


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

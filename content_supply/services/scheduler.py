"""APScheduler orchestration — RSS polling, hot tracking, cleanup, rewriting."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from content_supply.config import CONFIGS_DIR, load_app_config
from content_supply.db import init_db
from content_supply.services.feed_manager import FeedManager
from content_supply.services.rss_crawler import RSSCrawler
from content_supply.services.content_processor import ContentProcessor
from content_supply.services.item_writer import ItemWriter
from content_supply.services.hot_tracker import HotTracker
from content_supply.services.hot_content_fetcher import HotContentFetcher
from content_supply.services.content_rewriter import ContentRewriter
from content_supply.services.cleanup_manager import CleanupManager
from content_supply.services.notification import NotificationService
from content_supply.services.web_source_crawler import WebSourceCrawler
from content_supply.services.hot_content_fetcher import HotContentFetcher

logger = logging.getLogger(__name__)


class SchedulerOrchestrator:
    """Central scheduler for all content supply tasks."""

    def __init__(self, session_factory: async_sessionmaker):
        self.session_factory = session_factory
        self.config = load_app_config()
        self.scheduler = AsyncIOScheduler()
        self.rss_crawler = RSSCrawler()
        self.hot_tracker = HotTracker()
        self.content_rewriter = ContentRewriter()
        self.processor = ContentProcessor()
        self.web_source_crawler = WebSourceCrawler()
        self.notification = NotificationService(
            webhook_url=self.config.notification.webhook_url,
            auto_confirm_hours=self.config.notification.auto_confirm_after_hours,
        )

    async def _run_rss_feed(self, feed_id: int, url: str, source_name: str) -> None:
        """Execute RSS crawl for a single feed."""
        async with self.session_factory() as session:
            try:
                mgr = FeedManager(session)
                items = await self.rss_crawler.fetch(url, source_name=source_name)
                if not items:
                    logger.info(f"Feed {feed_id}: no items found")
                    await mgr.update_fetch_status(feed_id, True)
                    return

                writer = ItemWriter(session)
                count = 0
                for item in items:
                    item.extra["feed_id"] = feed_id
                    result = await writer.write(item, feed_id=feed_id)
                    if result:
                        count += 1

                await mgr.update_fetch_status(feed_id, True)
                await session.commit()
                logger.info(f"Feed {feed_id}: {count}/{len(items)} new items")
            except Exception as e:
                logger.error(f"Feed {feed_id} crawl failed: {e}")
                mgr = FeedManager(session)
                await mgr.update_fetch_status(feed_id, False, error=str(e))
                await session.commit()

    async def _run_hot_track(self) -> None:
        """Fetch hot keywords from all platforms."""
        async with self.session_factory() as session:
            try:
                results = await self.hot_tracker.fetch_all()
                from content_supply.models.hot_keyword import HotKeyword
                total = 0
                for platform, keywords in results.items():
                    for kw in keywords:
                        exists = await session.execute(
                            select(HotKeyword).where(
                                HotKeyword.keyword == kw.keyword,
                                HotKeyword.platform == kw.platform,
                                HotKeyword.fetched_at > datetime.now() - timedelta(hours=1),
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
                        session.add(hk)
                        total += 1
                await session.commit()
                logger.info(f"Hot track: {total} new keywords")
            except Exception as e:
                logger.error(f"Hot track failed: {e}")

    async def _run_hot_content_fetch(self) -> None:
        """Fetch related articles for unfetched hot keywords."""
        async with self.session_factory() as session:
            try:
                fetcher = HotContentFetcher()
                writer = ItemWriter(session)

                stmt = (
                    select(HotKeyword)
                    .where(HotKeyword.content_fetched == False)
                    .order_by(HotKeyword.hot_score.desc())
                    .limit(10)
                )
                result = await session.execute(stmt)
                keywords = list(result.scalars().all())

                if not keywords:
                    logger.info("Hot content fetch: no unfetched keywords")
                    return

                total_new = 0
                for kw in keywords:
                    try:
                        items = await fetcher.fetch_content(
                            keyword=kw.keyword,
                            platform=kw.platform,
                            max_results=3,
                        )
                        count = 0
                        for item in items:
                            r = await writer.write(item)
                            if r:
                                count += 1
                        total_new += count
                        kw.content_fetched = True
                        kw.status = "done"
                    except Exception as e:
                        logger.warning("Hot content fetch failed for '%s': %s", kw.keyword, e)
                        kw.status = "failed"

                await fetcher.close()
                await session.commit()
                logger.info(f"Hot content fetch: {len(keywords)} keywords, {total_new} new articles")
            except Exception as e:
                logger.error(f"Hot content fetch batch failed: {e}")

    async def _run_cleanup(self) -> None:
        """Run cleanup scan (generates pending reviews, does NOT auto-delete)."""
        async with self.session_factory() as session:
            try:
                policies = yaml.safe_load(
                    open(CONFIGS_DIR / "cleanup_policies.yaml")
                )
                mgr = CleanupManager(session, policies)
                logs = await mgr.scan_all()

                # Send notifications for pending reviews
                for log in logs:
                    log_dict = {
                        "id": log.id,
                        "policy": log.policy,
                        "source_type": log.source_type,
                        "items_to_delete": log.items_to_delete,
                        "pending_item_ids": log.pending_item_ids,
                        "auto_confirm_at": str(log.auto_confirm_at),
                        "items_scanned": log.items_scanned,
                    }
                    await self.notification.send_review_notification(log_dict)

                logger.info(f"Cleanup scan: {len(logs)} pending reviews created")
            except Exception as e:
                logger.error(f"Cleanup scan failed: {e}")

    async def _run_rewrite(self) -> None:
        """Rewrite eligible items (source_type configured for auto-rewrite)."""
        async with self.session_factory() as session:
            try:
                from content_supply.models.item import Item
                from content_supply.models.rewrite_task import RewriteTask

                stmt = (
                    select(Item)
                    .where(Item.is_rewritten == False, Item.status == "published")
                    .order_by(Item.quality_score.desc())
                    .limit(20)
                )
                result = await session.execute(stmt)
                items = list(result.scalars().all())

                for item in items:
                    content = item.content or item.summary or ""
                    if len(content) < 100:
                        continue
                    try:
                        rw_result = await self.content_rewriter.rewrite(content, "paraphrase")
                        item.original_content = item.content
                        item.content = rw_result["rewritten"]
                        item.is_rewritten = True

                        task = RewriteTask(
                            item_id=item.id,
                            rewrite_type="paraphrase",
                            status="done",
                            original_hash=item.content_hash,
                            llm_model=rw_result["model"],
                            prompt_used=rw_result["prompt_used"],
                        )
                        session.add(task)
                        item.rewrite_task_id = task.id if task.id else None
                    except Exception as e:
                        logger.warning(f"Rewrite failed for {item.id}: {e}")

                await session.commit()
                logger.info(f"Rewrite: processed {len(items)} items")
            except Exception as e:
                logger.error(f"Rewrite batch failed: {e}")

    def _load_active_feeds(self) -> list[dict]:
        """Load active feeds from config."""
        feeds_config = yaml.safe_load(
            open(CONFIGS_DIR / "feeds.yaml")
        )
        return feeds_config.get("feeds", [])

    def _load_web_sources(self) -> list[dict]:
        """Load web source configs."""
        try:
            ws_config = yaml.safe_load(
                open(CONFIGS_DIR / "web_sources.yaml")
            )
            return [s for s in ws_config.get("web_sources", []) if s.get("enabled", False)]
        except FileNotFoundError:
            logger.info("No web_sources.yaml found, skipping web source scheduling")
            return []

    async def _run_web_source(self, name: str, source_config: dict) -> None:
        """Execute web source crawl for a configured site."""
        async with self.session_factory() as session:
            try:
                from content_supply.services.item_writer import ItemWriter
                from content_supply.models.crawl_task import CrawlTask
                from datetime import datetime

                task = CrawlTask(
                    url=source_config["url"],
                    task_type="web",
                    status="running",
                )
                session.add(task)
                await session.flush()

                items = await self.web_source_crawler.crawl_source(source_config)
                task.items_found = len(items)

                writer = ItemWriter(session)
                count = 0
                for item in items:
                    result = await writer.write(item)
                    if result:
                        count += 1

                task.items_new = count
                task.status = "done"
                task.finished_at = datetime.now()
                await session.commit()
                logger.info(
                    "WebSource '%s': found=%d new=%d", name, len(items), count
                )
            except Exception as e:
                logger.error("WebSource '%s' crawl failed: %s", name, e)
                try:
                    task.status = "failed"
                    task.error_message = str(e)
                    task.finished_at = datetime.now()
                    await session.commit()
                except Exception:
                    pass

    def start(self) -> None:
        """Register all jobs and start the scheduler."""
        cfg = self.config.scheduler

        # Register RSS feed jobs
        feeds = self._load_active_feeds()
        for i, feed in enumerate(feeds):
            self.scheduler.add_job(
                self._run_rss_feed,
                IntervalTrigger(seconds=feed.get("poll_interval", cfg.rss_default_interval)),
                id=f"rss_feed_{i}",
                name=f"RSS: {feed['name']}",
                kwargs={"feed_id": i, "url": feed["url"], "source_name": feed["name"]},
            )

        # Hot keyword tracking
        if cfg.hot_track_interval > 0:
            self.scheduler.add_job(
                self._run_hot_track,
                IntervalTrigger(seconds=cfg.hot_track_interval),
                id="hot_track",
                name="Hot Keyword Tracking",
            )

        # Hot keyword → content fetching (runs after keywords are collected)
        hot_content_interval = getattr(cfg, "hot_content_fetch_interval", 0)
        if hot_content_interval > 0:
            self.scheduler.add_job(
                self._run_hot_content_fetch,
                IntervalTrigger(seconds=hot_content_interval),
                id="hot_content_fetch",
                name="Hot Content Fetch",
            )

        # Web source crawling
        web_sources = self._load_web_sources()
        for i, ws in enumerate(web_sources):
            self.scheduler.add_job(
                self._run_web_source,
                IntervalTrigger(seconds=ws.get("poll_interval", cfg.rss_default_interval)),
                id=f"web_source_{i}",
                name=f"WebSource: {ws['name']}",
                kwargs={"name": ws["name"], "source_config": ws},
            )

        # Cleanup scan
        if cfg.cleanup_cron:
            parts = cfg.cleanup_cron.split()
            self.scheduler.add_job(
                self._run_cleanup,
                CronTrigger(
                    minute=parts[0], hour=parts[1],
                    day=parts[2], month=parts[3], day_of_week=parts[4],
                ),
                id="cleanup_scan",
                name="Cleanup Scan",
            )

        # Content rewriting
        if cfg.rewrite_cron:
            parts = cfg.rewrite_cron.split()
            self.scheduler.add_job(
                self._run_rewrite,
                CronTrigger(
                    minute=parts[0], hour=parts[1],
                    day=parts[2], month=parts[3], day_of_week=parts[4],
                ),
                id="rewrite_batch",
                name="Batch Content Rewrite",
            )

        # Auto-confirm checker (every hour)
        self.scheduler.add_job(
            self._check_auto_confirm,
            IntervalTrigger(hours=1),
            id="auto_confirm_check",
            name="Auto Confirm Checker",
        )

        self.scheduler.start()
        logger.info(
            f"Scheduler started with {len(self.scheduler.get_jobs())} jobs"
        )

    def stop(self) -> None:
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    async def _check_auto_confirm(self) -> None:
        """Check and auto-execute expired pending reviews."""
        async with self.session_factory() as session:
            try:
                policies = yaml.safe_load(
                    open(CONFIGS_DIR / "cleanup_policies.yaml")
                )
                mgr = CleanupManager(session, policies)
                auto_ids = await mgr.check_auto_confirm()
                if auto_ids:
                    logger.info(f"Auto-confirmed cleanups: {auto_ids}")
            except Exception as e:
                logger.error(f"Auto-confirm check failed: {e}")

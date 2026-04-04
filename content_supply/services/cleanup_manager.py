"""Cleanup manager — TTL / capacity / quality strategies with review workflow."""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from content_supply.models.cleanup_log import CleanupLog
from content_supply.models.item import Item

logger = logging.getLogger(__name__)


class CleanupManager:
    """Scan and manage expired content with review-then-delete workflow."""

    def __init__(self, session: AsyncSession, policies: dict, redis_client=None):
        self.session = session
        self.policies = policies  # from cleanup_policies.yaml
        self.redis = redis_client

    async def scan_ttl(self, source_type: str, ttl_days: int) -> list[str]:
        """Find item IDs older than TTL for a given source_type."""
        cutoff = datetime.now() - timedelta(days=ttl_days)
        stmt = (
            select(Item.id)
            .where(Item.source_type == source_type, Item.created_at < cutoff)
            .order_by(Item.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def scan_cold_start(self, source_type: str, cold_start_days: int) -> list[str]:
        """Find items with zero exposure/clicks after cold_start_days."""
        cutoff = datetime.now() - timedelta(days=cold_start_days)
        stmt = (
            select(Item.id)
            .where(
                Item.source_type == source_type,
                Item.exposure_count == 0,
                Item.click_count == 0,
                Item.created_at < cutoff,
            )
            .order_by(Item.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def scan_capacity(self, source_type: str, max_items: int) -> list[str]:
        """Find items to evict when count exceeds max_items (lowest quality first)."""
        # Count current items
        count_stmt = select(func.count()).select_from(Item).where(Item.source_type == source_type)
        total = (await self.session.execute(count_stmt)).scalar() or 0

        if total <= max_items:
            return []

        excess = total - max_items
        # Select lowest quality + oldest to evict
        stmt = (
            select(Item.id)
            .where(Item.source_type == source_type)
            .order_by(Item.quality_score.asc(), Item.created_at.asc())
            .limit(excess)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def scan_quality(self, source_type: str, min_quality: float) -> list[str]:
        """Find items below quality threshold (preserve last 24h)."""
        recent_cutoff = datetime.now() - timedelta(hours=24)
        stmt = (
            select(Item.id)
            .where(
                Item.source_type == source_type,
                Item.quality_score < min_quality,
                Item.created_at < recent_cutoff,
            )
            .order_by(Item.quality_score.asc())
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def scan_all(self) -> list[CleanupLog]:
        """Run all cleanup scans and create pending review logs.

        Returns list of CleanupLog objects with status='pending_review'.
        """
        logs = []
        policy_list = self.policies.get("policies", [])

        for policy in policy_list:
            source_type = policy["source_type"]
            all_ids = set()

            # TTL scan
            ttl_ids = await self.scan_ttl(source_type, policy.get("ttl_days", 30))
            all_ids.update(ttl_ids)

            # Cold start scan
            cold_days = policy.get("cold_start_ttl_days")
            if cold_days:
                cold_ids = await self.scan_cold_start(source_type, cold_days)
                all_ids.update(cold_ids)

            # Capacity scan
            max_items = policy.get("max_items", 10000)
            cap_ids = await self.scan_capacity(source_type, max_items)
            all_ids.update(cap_ids)

            # Quality scan
            min_quality = policy.get("min_quality", 0.2)
            qual_ids = await self.scan_quality(source_type, min_quality)
            all_ids.update(qual_ids)

            if not all_ids:
                continue

            # Count total items for scan stats
            total_count = (await self.session.execute(
                select(func.count()).select_from(Item).where(Item.source_type == source_type)
            )).scalar() or 0

            log = CleanupLog(
                policy="combined",
                source_type=source_type,
                status="pending_review",
                items_scanned=total_count,
                items_to_delete=len(all_ids),
                pending_item_ids=json.dumps(sorted(all_ids)),
                details=json.dumps({
                    "ttl_ids": len(ttl_ids),
                    "cold_start_ids": len(cold_ids if cold_days else []),
                    "capacity_ids": len(cap_ids),
                    "quality_ids": len(qual_ids),
                }),
                auto_confirm_at=datetime.now() + timedelta(
                    hours=self.policies.get("auto_confirm_after_hours", 24)
                ),
            )
            self.session.add(log)
            await self.session.flush()
            logs.append(log)

        if logs:
            await self.session.commit()

        return logs

    async def execute_cleanup(self, log_id: int, reviewer: str = "system") -> int:
        """Execute the pending cleanup after review approval.

        Returns number of items actually deleted.
        """
        result = await self.session.execute(
            select(CleanupLog).where(CleanupLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            raise ValueError(f"CleanupLog {log_id} not found")
        if log.status not in ("pending_review", "approved"):
            raise ValueError(f"Log {log_id} status is {log.status}, cannot execute")

        log.status = "executing"
        log.reviewed_by = reviewer
        log.reviewed_at = datetime.now()
        log.started_at = datetime.now()
        await self.session.flush()

        item_ids = json.loads(log.pending_item_ids or "[]")
        deleted_count = 0

        for item_id in item_ids:
            # Delete from MySQL
            await self.session.execute(delete(Item).where(Item.id == item_id))
            deleted_count += 1

            # Remove from Redis
            if self.redis:
                try:
                    pipe = self.redis.pipeline()
                    pipe.srem("item_pool:all", item_id)
                    pipe.zrem("hot_items:global", item_id)
                    await pipe.execute()
                except Exception as e:
                    logger.warning(f"Redis cleanup failed for {item_id}: {e}")

        log.status = "done"
        log.items_deleted = deleted_count
        log.finished_at = datetime.now()
        await self.session.commit()

        logger.info(f"Cleanup {log_id}: deleted {deleted_count} items for {log.source_type}")
        return deleted_count

    async def reject_cleanup(self, log_id: int, reviewer: str = "manual") -> None:
        """Reject a pending cleanup (mark as rejected, extend item TTL)."""
        result = await self.session.execute(
            select(CleanupLog).where(CleanupLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        if not log:
            raise ValueError(f"CleanupLog {log_id} not found")

        log.status = "rejected"
        log.reviewed_by = reviewer
        log.reviewed_at = datetime.now()
        log.finished_at = datetime.now()
        await self.session.commit()

    async def check_auto_confirm(self) -> list[int]:
        """Check for pending reviews past auto_confirm_at, auto-execute them."""
        now = datetime.now()
        stmt = select(CleanupLog).where(
            CleanupLog.status == "pending_review",
            CleanupLog.auto_confirm_at < now,
        )
        result = await self.session.execute(stmt)
        auto_executed = []
        for log in result.scalars().all():
            try:
                count = await self.execute_cleanup(log.id, reviewer="auto_timeout")
                auto_executed.append(log.id)
                logger.info(f"Auto-confirmed cleanup {log.id}: {count} items deleted")
            except Exception as e:
                logger.error(f"Auto-confirm cleanup {log.id} failed: {e}")
        return auto_executed

    async def get_pending_reviews(self) -> list[CleanupLog]:
        """Get all pending review cleanup logs."""
        stmt = select(CleanupLog).where(
            CleanupLog.status == "pending_review"
        ).order_by(CleanupLog.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_cleanup_logs(
        self, limit: int = 50, offset: int = 0
    ) -> list[CleanupLog]:
        """Get cleanup history."""
        stmt = (
            select(CleanupLog)
            .order_by(CleanupLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

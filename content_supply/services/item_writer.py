"""Item writer — MySQL + Redis integration."""

import json
import logging
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from content_supply.models.item import Item
from content_supply.services.content_processor import ContentProcessor
from content_supply.services.types import CrawledItem

logger = logging.getLogger(__name__)


class ItemWriter:
    """Write processed items to MySQL and push to Redis."""

    def __init__(
        self,
        session: AsyncSession,
        redis_client: Optional[aioredis.Redis] = None,
    ):
        self.session = session
        self.redis = redis_client
        self.processor = ContentProcessor()

    async def write(
        self,
        item: CrawledItem,
        feed_id: int = None,
    ) -> Optional[Item]:
        """Write a single CrawledItem to DB. Returns None if duplicate."""
        # 1. Compute content_hash and item_id
        content_hash = self.processor.compute_content_hash(item)
        item_id = self.processor.generate_item_id(item)

        # 2. Check if URL or content_hash already exists
        stmt = select(Item).where(
            (Item.url == item.url) | (Item.content_hash == content_hash)
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing is not None:
            logger.debug("Duplicate item skipped: url=%s", item.url)
            return None

        # 3. Extract tags and quality score
        tags = self.processor.extract_tags(item)
        # Enrich the CrawledItem with extracted tags before scoring
        item.tags = tags
        quality_score = self.processor.score_quality(item)

        # 4. Create Item ORM object
        db_item = Item(
            id=item_id,
            title=item.title,
            summary=item.summary or None,
            content=item.content or None,
            original_content=item.content or None,
            url=item.url,
            image_url=item.image_url or None,
            author=item.author or None,
            source_name=item.source_name or None,
            source_type=item.source_type,
            feed_id=feed_id,
            tags=json.dumps(tags, ensure_ascii=False) if tags else None,
            quality_score=quality_score,
            content_hash=content_hash,
            published_at=item.published_at,
        )
        self.session.add(db_item)

        # 5. Flush to persist
        await self.session.flush()

        # 6. Push to Redis
        await self._push_to_redis(item_id, quality_score)

        logger.info("Item written: id=%s title=%.60s", item_id, item.title)
        return db_item

    async def write_batch(
        self,
        items: list[CrawledItem],
        feed_id: int = None,
    ) -> int:
        """Write a batch of items. Returns count of newly inserted items."""
        count = 0
        for item in items:
            result = await self.write(item, feed_id=feed_id)
            if result is not None:
                count += 1
        return count

    async def _push_to_redis(self, item_id: str, quality_score: float) -> None:
        """Push item ID to Redis pools."""
        if not self.redis:
            return
        try:
            pipe = self.redis.pipeline()
            pipe.sadd("item_pool:all", item_id)
            pipe.zadd("hot_items:global", {item_id: quality_score})
            await pipe.execute()
        except Exception as e:
            logger.warning("Redis push failed for %s: %s", item_id, e)

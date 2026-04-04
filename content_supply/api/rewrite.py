"""Rewrite API — trigger LLM content rewriting."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from content_supply.api.deps import get_db
from content_supply.models.item import Item
from content_supply.models.rewrite_task import RewriteTask
from content_supply.schemas.task import CrawlTaskResponse

router = APIRouter()


@router.post("/rewrite/{item_id}")
async def rewrite_item(
    item_id: str,
    rewrite_type: str = "paraphrase",
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger rewrite for a single item."""
    from content_supply.services.content_rewriter import ContentRewriter

    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")
    if item.is_rewritten:
        return {"status": "already_rewritten", "item_id": item_id}

    content = item.content or item.summary or ""
    if not content:
        raise HTTPException(400, "Item has no content to rewrite")

    rewriter = ContentRewriter()

    # Create rewrite task
    task = RewriteTask(
        item_id=item_id,
        rewrite_type=rewrite_type,
        status="running",
        original_hash=item.content_hash,
    )
    db.add(task)
    await db.flush()

    try:
        rw_result = await rewriter.rewrite(content, rewrite_type)

        # Update item
        item.original_content = item.content
        item.content = rw_result["rewritten"]
        item.is_rewritten = True

        # Update task
        task.status = "done"
        task.llm_model = rw_result["model"]
        task.prompt_used = rw_result["prompt_used"]
        item.rewrite_task_id = task.id

        await db.commit()
        return {
            "status": "done",
            "item_id": item_id,
            "rewrite_type": rewrite_type,
            "model": rw_result["model"],
            "tokens_used": rw_result["tokens_used"],
        }
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        await db.commit()
        raise HTTPException(500, f"Rewrite failed: {e}")


@router.post("/rewrite/batch")
async def rewrite_batch(
    source_type: Optional[str] = None,
    min_quality: float = 0.0,
    limit: int = 20,
    rewrite_type: str = "paraphrase",
    db: AsyncSession = Depends(get_db),
):
    """Batch trigger rewrite for eligible items."""
    from content_supply.services.content_rewriter import ContentRewriter

    stmt = (
        select(Item)
        .where(Item.is_rewritten == False, Item.status == "published")
        .order_by(Item.quality_score.desc())
        .limit(limit)
    )
    if source_type:
        stmt = stmt.where(Item.source_type == source_type)
    if min_quality > 0:
        stmt = stmt.where(Item.quality_score >= min_quality)

    result = await db.execute(stmt)
    items = list(result.scalars().all())

    rewriter = ContentRewriter()
    processed = 0
    failed = 0

    for item in items:
        content = item.content or item.summary or ""
        if len(content) < 100:
            continue
        try:
            rw_result = await rewriter.rewrite(content, rewrite_type)

            task = RewriteTask(
                item_id=item.id,
                rewrite_type=rewrite_type,
                status="done",
                original_hash=item.content_hash,
                llm_model=rw_result["model"],
                prompt_used=rw_result["prompt_used"],
            )
            db.add(task)
            await db.flush()

            item.original_content = item.content
            item.content = rw_result["rewritten"]
            item.is_rewritten = True
            item.rewrite_task_id = task.id
            processed += 1
        except Exception:
            failed += 1

    await db.commit()
    return {
        "status": "done",
        "processed": processed,
        "failed": failed,
        "total_candidates": len(items),
    }

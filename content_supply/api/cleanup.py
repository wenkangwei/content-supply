"""Cleanup API — policies, scan trigger, review workflow, logs."""

from typing import Optional

import yaml
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from content_supply.api.deps import get_db
from content_supply.config import load_app_config, CONFIGS_DIR
from content_supply.models.cleanup_log import CleanupLog
from content_supply.schemas.cleanup import CleanupLogResponse, CleanupPolicyResponse, CleanupReviewRequest

router = APIRouter()


@router.get("/cleanup/policies", response_model=list[CleanupPolicyResponse])
async def get_cleanup_policies():
    """Get all configured cleanup policies."""
    config_path = CONFIGS_DIR / "cleanup_policies.yaml"
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get("policies", [])


@router.post("/cleanup/trigger")
async def trigger_cleanup_scan(db: AsyncSession = Depends(get_db)):
    """Trigger a cleanup scan. Generates pending reviews, does NOT auto-delete."""
    from content_supply.services.notification import NotificationService
    config_path = CONFIGS_DIR / "cleanup_policies.yaml"
    with open(config_path) as f:
        policies = yaml.safe_load(f)

    from content_supply.services.cleanup_manager import CleanupManager
    mgr = CleanupManager(db, policies)
    logs = await mgr.scan_all()

    # Send notifications
    app_config = load_app_config()
    notifier = NotificationService(
        webhook_url=app_config.notification.webhook_url,
        auto_confirm_hours=app_config.notification.auto_confirm_after_hours,
    )
    for log in logs:
        await notifier.send_review_notification({
            "id": log.id,
            "policy": log.policy,
            "source_type": log.source_type,
            "items_to_delete": log.items_to_delete,
            "pending_item_ids": log.pending_item_ids,
            "auto_confirm_at": str(log.auto_confirm_at),
            "items_scanned": log.items_scanned,
        })

    return {
        "status": "scan_complete",
        "pending_reviews": len(logs),
        "reviews": [
            {
                "id": log.id,
                "source_type": log.source_type,
                "items_to_delete": log.items_to_delete,
                "auto_confirm_at": str(log.auto_confirm_at),
            }
            for log in logs
        ],
    }


@router.get("/cleanup/pending", response_model=list[CleanupLogResponse])
async def get_pending_reviews(db: AsyncSession = Depends(get_db)):
    """Get all pending cleanup reviews awaiting approval."""
    from content_supply.services.cleanup_manager import CleanupManager
    config_path = CONFIGS_DIR / "cleanup_policies.yaml"
    with open(config_path) as f:
        policies = yaml.safe_load(f)
    mgr = CleanupManager(db, policies)
    return await mgr.get_pending_reviews()


@router.post("/cleanup/{log_id}/confirm")
async def confirm_cleanup(
    log_id: int, review: CleanupReviewRequest, db: AsyncSession = Depends(get_db)
):
    """Confirm and execute a pending cleanup deletion."""
    from content_supply.services.cleanup_manager import CleanupManager
    config_path = CONFIGS_DIR / "cleanup_policies.yaml"
    with open(config_path) as f:
        policies = yaml.safe_load(f)
    mgr = CleanupManager(db, policies)
    try:
        count = await mgr.execute_cleanup(log_id, reviewer=review.reviewer)
        return {"status": "done", "items_deleted": count, "log_id": log_id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/cleanup/{log_id}/reject")
async def reject_cleanup(
    log_id: int, review: CleanupReviewRequest, db: AsyncSession = Depends(get_db)
):
    """Reject a pending cleanup (items will not be deleted)."""
    from content_supply.services.cleanup_manager import CleanupManager
    config_path = CONFIGS_DIR / "cleanup_policies.yaml"
    with open(config_path) as f:
        policies = yaml.safe_load(f)
    mgr = CleanupManager(db, policies)
    try:
        await mgr.reject_cleanup(log_id, reviewer=review.reviewer)
        return {"status": "rejected", "log_id": log_id}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/cleanup/logs", response_model=list[CleanupLogResponse])
async def get_cleanup_logs(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get cleanup history."""
    from content_supply.services.cleanup_manager import CleanupManager
    config_path = CONFIGS_DIR / "cleanup_policies.yaml"
    with open(config_path) as f:
        policies = yaml.safe_load(f)
    mgr = CleanupManager(db, policies)
    return await mgr.get_cleanup_logs(limit=limit, offset=offset)

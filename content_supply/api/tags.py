"""Tags API — tag mining endpoints (placeholder)."""

from fastapi import APIRouter

from content_supply.services.tag_miner import TagMiner

router = APIRouter()

_miner = TagMiner()


@router.post("/tags/mine")
async def trigger_tag_mining(
    min_quality: float = 0.5,
    limit: int = 100,
):
    """Trigger LLM-based tag mining for quality content (placeholder)."""
    result = await _miner.trigger_mining(min_quality=min_quality, limit=limit)
    return result


@router.get("/tags/status")
async def get_tag_mining_status():
    """Get current tag mining task status."""
    return await _miner.get_status()

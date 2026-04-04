"""Items API — list, detail, search."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from content_supply.api.deps import get_db
from content_supply.models.item import Item
from content_supply.schemas.item import ItemListParams, ItemResponse, ItemSearchParams

router = APIRouter()


@router.get("/items", response_model=list[ItemResponse])
async def list_items(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = Query(default="created_at"),
    sort_desc: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    """List items with filtering and pagination."""
    stmt = select(Item)
    if source_type:
        stmt = stmt.where(Item.source_type == source_type)
    if category:
        stmt = stmt.where(Item.category == category)
    if status:
        stmt = stmt.where(Item.status == status)

    # Sort
    sort_col = getattr(Item, sort_by, Item.created_at)
    stmt = stmt.order_by(sort_col.desc() if sort_desc else sort_col.asc())

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/items/count")
async def count_items(
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Count items by filters."""
    stmt = select(func.count()).select_from(Item)
    if source_type:
        stmt = stmt.where(Item.source_type == source_type)
    if status:
        stmt = stmt.where(Item.status == status)
    total = (await db.execute(stmt)).scalar() or 0
    return {"total": total}


@router.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str, db: AsyncSession = Depends(get_db)):
    """Get item by ID."""
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")
    return item


@router.post("/items/search", response_model=list[ItemResponse])
async def search_items(data: ItemSearchParams, db: AsyncSession = Depends(get_db)):
    """Search items by keyword in title/content."""
    pattern = f"%{data.query}%"
    stmt = select(Item).where(
        or_(Item.title.ilike(pattern), Item.summary.ilike(pattern))
    )
    if data.source_type:
        stmt = stmt.where(Item.source_type == data.source_type)
    offset = (data.page - 1) * data.page_size
    stmt = stmt.offset(offset).limit(data.page_size).order_by(Item.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.put("/items/{item_id}/status")
async def update_item_status(
    item_id: str, status: str = "archived", db: AsyncSession = Depends(get_db)
):
    """Update item status (e.g., archive)."""
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, "Item not found")
    item.status = status
    await db.commit()
    return {"id": item_id, "status": status}

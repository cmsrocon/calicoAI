import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.news_item import NewsItem, NewsItemVendor
from app.models.trend import Trend
from app.models.vendor import Vendor
from app.schemas.trend import TrendResponse
from app.schemas.vendor import VendorResponse, VendorSummary
from app.services.vendor_service import get_vendor, list_vendors

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=dict)
async def list_vendors_endpoint(
    search: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    vendors, total = await list_vendors(db, search, page, page_size)
    items = []
    for v in vendors:
        count_result = await db.execute(
            select(func.count()).select_from(NewsItemVendor).where(NewsItemVendor.vendor_id == v.id)
        )
        count = count_result.scalar() or 0
        items.append(VendorSummary(id=v.id, name=v.name, slug=v.slug, description=v.description, news_count=count))
    return {"vendors": [i.model_dump() for i in items], "total": total}


@router.get("/{vendor_id}")
async def get_vendor_detail(vendor_id: int, db: AsyncSession = Depends(get_db)):
    vendor = await get_vendor(db, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    count = (await db.execute(
        select(func.count()).select_from(NewsItemVendor).where(NewsItemVendor.vendor_id == vendor_id)
    )).scalar() or 0
    recent_ids = (await db.execute(
        select(NewsItemVendor.news_item_id)
        .where(NewsItemVendor.vendor_id == vendor_id)
        .order_by(NewsItemVendor.news_item_id.desc())
        .limit(5)
    )).scalars().all()
    recent = (await db.execute(select(NewsItem).where(NewsItem.id.in_(recent_ids)))).scalars().all()
    trend = (await db.execute(
        select(Trend).where(Trend.trend_type == "vendor", Trend.entity_id == vendor_id)
        .order_by(Trend.generated_at.desc())
    )).scalar_one_or_none()
    return {
        "id": vendor.id, "name": vendor.name, "slug": vendor.slug,
        "description": vendor.description,
        "aliases": json.loads(vendor.aliases or "[]"),
        "is_active": vendor.is_active, "news_count": count,
        "recent_news": [{"id": i.id, "headline": i.headline, "importance_rank": i.importance_rank} for i in recent],
        "trend": TrendResponse(
            id=trend.id, trend_type=trend.trend_type, entity_id=trend.entity_id,
            period_start=trend.period_start, period_end=trend.period_end,
            narrative=trend.narrative, sentiment_score=trend.sentiment_score,
            top_themes=json.loads(trend.top_themes or "[]"),
            item_count=trend.item_count, generated_at=trend.generated_at,
        ).model_dump() if trend else None,
    }


@router.get("/{vendor_id}/news")
async def get_vendor_news(
    vendor_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    vendor = await get_vendor(db, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    item_ids = (await db.execute(
        select(NewsItemVendor.news_item_id).where(NewsItemVendor.vendor_id == vendor_id)
    )).scalars().all()
    items = (await db.execute(
        select(NewsItem).where(NewsItem.id.in_(item_ids))
        .order_by(NewsItem.importance_rank.desc().nullslast(), NewsItem.ingested_at.desc())
    )).scalars().all()
    total = len(items)
    offset = (page - 1) * page_size
    page_items = items[offset:offset + page_size]
    return {
        "items": [{"id": i.id, "headline": i.headline, "published_at": i.published_at, "importance_rank": i.importance_rank} for i in page_items],
        "total": total,
    }


@router.get("/{vendor_id}/trends", response_model=list[TrendResponse])
async def get_vendor_trends(vendor_id: int, db: AsyncSession = Depends(get_db)):
    vendor = await get_vendor(db, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    trends = (await db.execute(
        select(Trend).where(Trend.trend_type == "vendor", Trend.entity_id == vendor_id)
        .order_by(Trend.generated_at.desc())
        .limit(10)
    )).scalars().all()
    return [TrendResponse(
        id=t.id, trend_type=t.trend_type, entity_id=t.entity_id,
        period_start=t.period_start, period_end=t.period_end,
        narrative=t.narrative, sentiment_score=t.sentiment_score,
        top_themes=json.loads(t.top_themes or "[]"),
        item_count=t.item_count, generated_at=t.generated_at,
    ) for t in trends]

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.news_item import NewsItem, NewsItemVertical
from app.models.trend import Trend
from app.models.vertical import Vertical
from app.schemas.trend import TrendResponse
from app.schemas.vertical import VerticalSummary
from app.services.vertical_service import get_vertical, list_verticals

router = APIRouter(prefix="/verticals", tags=["verticals"])


@router.get("")
async def list_verticals_endpoint(search: str = "", db: AsyncSession = Depends(get_db)):
    verticals = await list_verticals(db, search)
    items = []
    for v in verticals:
        count = (await db.execute(
            select(func.count()).select_from(NewsItemVertical).where(NewsItemVertical.vertical_id == v.id)
        )).scalar() or 0
        items.append(VerticalSummary(id=v.id, name=v.name, slug=v.slug, icon_name=v.icon_name, news_count=count))
    return {"verticals": [i.model_dump() for i in items], "total": len(items)}


@router.get("/{vertical_id}")
async def get_vertical_detail(vertical_id: int, db: AsyncSession = Depends(get_db)):
    vertical = await get_vertical(db, vertical_id)
    if not vertical:
        raise HTTPException(status_code=404, detail="Vertical not found")
    count = (await db.execute(
        select(func.count()).select_from(NewsItemVertical).where(NewsItemVertical.vertical_id == vertical_id)
    )).scalar() or 0
    recent_ids = (await db.execute(
        select(NewsItemVertical.news_item_id).where(NewsItemVertical.vertical_id == vertical_id)
        .order_by(NewsItemVertical.news_item_id.desc()).limit(5)
    )).scalars().all()
    recent = (await db.execute(select(NewsItem).where(NewsItem.id.in_(recent_ids)))).scalars().all()
    trend = (await db.execute(
        select(Trend).where(Trend.trend_type == "vertical", Trend.entity_id == vertical_id)
        .order_by(Trend.generated_at.desc())
    )).scalar_one_or_none()
    return {
        "id": vertical.id, "name": vertical.name, "slug": vertical.slug,
        "description": vertical.description, "icon_name": vertical.icon_name,
        "news_count": count,
        "recent_news": [{"id": i.id, "headline": i.headline, "importance_rank": i.importance_rank} for i in recent],
        "trend": TrendResponse(
            id=trend.id, trend_type=trend.trend_type, entity_id=trend.entity_id,
            period_start=trend.period_start, period_end=trend.period_end,
            narrative=trend.narrative, sentiment_score=trend.sentiment_score,
            top_themes=json.loads(trend.top_themes or "[]"),
            item_count=trend.item_count, generated_at=trend.generated_at,
        ).model_dump() if trend else None,
    }


@router.get("/{vertical_id}/news")
async def get_vertical_news(
    vertical_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    vertical = await get_vertical(db, vertical_id)
    if not vertical:
        raise HTTPException(status_code=404, detail="Vertical not found")
    item_ids = (await db.execute(
        select(NewsItemVertical.news_item_id).where(NewsItemVertical.vertical_id == vertical_id)
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


@router.get("/{vertical_id}/trends", response_model=list[TrendResponse])
async def get_vertical_trends(vertical_id: int, db: AsyncSession = Depends(get_db)):
    vertical = await get_vertical(db, vertical_id)
    if not vertical:
        raise HTTPException(status_code=404, detail="Vertical not found")
    trends = (await db.execute(
        select(Trend).where(Trend.trend_type == "vertical", Trend.entity_id == vertical_id)
        .order_by(Trend.generated_at.desc()).limit(10)
    )).scalars().all()
    return [TrendResponse(
        id=t.id, trend_type=t.trend_type, entity_id=t.entity_id,
        period_start=t.period_start, period_end=t.period_end,
        narrative=t.narrative, sentiment_score=t.sentiment_score,
        top_themes=json.loads(t.top_themes or "[]"),
        item_count=t.item_count, generated_at=t.generated_at,
    ) for t in trends]

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
async def list_verticals_endpoint(search: str = "", topic_id: int | None = None, db: AsyncSession = Depends(get_db)):
    verticals = await list_verticals(db, search)
    items = []
    for v in verticals:
        count_query = (
            select(func.count())
            .select_from(NewsItemVertical)
            .join(NewsItem, NewsItem.id == NewsItemVertical.news_item_id)
            .where(NewsItemVertical.vertical_id == v.id)
        )
        if topic_id is not None:
            count_query = count_query.where(NewsItem.topic_id == topic_id)
        count = (await db.execute(count_query)).scalar() or 0
        items.append(VerticalSummary(id=v.id, name=v.name, slug=v.slug, icon_name=v.icon_name, news_count=count))
    visible_items = [item for item in items if item.news_count > 0 or topic_id is None]
    return {"verticals": [i.model_dump() for i in visible_items], "total": len(visible_items)}


@router.get("/{vertical_id}")
async def get_vertical_detail(vertical_id: int, topic_id: int | None = None, db: AsyncSession = Depends(get_db)):
    vertical = await get_vertical(db, vertical_id)
    if not vertical:
        raise HTTPException(status_code=404, detail="Vertical not found")
    count_query = (
        select(func.count())
        .select_from(NewsItemVertical)
        .join(NewsItem, NewsItem.id == NewsItemVertical.news_item_id)
        .where(NewsItemVertical.vertical_id == vertical_id)
    )
    recent_query = (
        select(NewsItemVertical.news_item_id)
        .join(NewsItem, NewsItem.id == NewsItemVertical.news_item_id)
        .where(NewsItemVertical.vertical_id == vertical_id)
    )
    if topic_id is not None:
        count_query = count_query.where(NewsItem.topic_id == topic_id)
        recent_query = recent_query.where(NewsItem.topic_id == topic_id)
    count = (await db.execute(count_query)).scalar() or 0
    recent_ids = (await db.execute(
        recent_query.order_by(NewsItem.ingested_at.desc()).limit(5)
    )).scalars().all()
    recent = (await db.execute(select(NewsItem).where(NewsItem.id.in_(recent_ids)))).scalars().all()
    trend_query = select(Trend).where(Trend.trend_type == "vertical", Trend.entity_id == vertical_id)
    if topic_id is None:
        trend_query = trend_query.where(Trend.topic_id.is_(None))
    else:
        trend_query = trend_query.where(Trend.topic_id == topic_id)
    trend = (await db.execute(trend_query.order_by(Trend.generated_at.desc()))).scalar_one_or_none()
    return {
        "id": vertical.id, "name": vertical.name, "slug": vertical.slug,
        "description": vertical.description, "icon_name": vertical.icon_name,
        "news_count": count,
        "recent_news": [{"id": i.id, "headline": i.headline, "importance_rank": i.importance_rank} for i in recent],
        "trend": TrendResponse(
            id=trend.id, topic_id=trend.topic_id, topic_name=None, trend_type=trend.trend_type, entity_id=trend.entity_id,
            period_start=trend.period_start, period_end=trend.period_end,
            narrative=trend.narrative, sentiment_score=trend.sentiment_score,
            top_themes=json.loads(trend.top_themes or "[]"),
            item_count=trend.item_count, generated_at=trend.generated_at,
        ).model_dump() if trend else None,
    }


@router.get("/{vertical_id}/news")
async def get_vertical_news(
    vertical_id: int,
    topic_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    vertical = await get_vertical(db, vertical_id)
    if not vertical:
        raise HTTPException(status_code=404, detail="Vertical not found")
    item_query = (
        select(NewsItem)
        .join(NewsItemVertical, NewsItemVertical.news_item_id == NewsItem.id)
        .where(NewsItemVertical.vertical_id == vertical_id)
    )
    if topic_id is not None:
        item_query = item_query.where(NewsItem.topic_id == topic_id)
    items = (await db.execute(
        item_query.order_by(NewsItem.importance_rank.desc().nullslast(), NewsItem.ingested_at.desc())
    )).scalars().all()
    total = len(items)
    offset = (page - 1) * page_size
    page_items = items[offset:offset + page_size]
    return {
        "items": [{"id": i.id, "headline": i.headline, "published_at": i.published_at, "importance_rank": i.importance_rank} for i in page_items],
        "total": total,
    }


@router.get("/{vertical_id}/trends", response_model=list[TrendResponse])
async def get_vertical_trends(vertical_id: int, topic_id: int | None = None, db: AsyncSession = Depends(get_db)):
    vertical = await get_vertical(db, vertical_id)
    if not vertical:
        raise HTTPException(status_code=404, detail="Vertical not found")
    trend_query = select(Trend).where(Trend.trend_type == "vertical", Trend.entity_id == vertical_id)
    if topic_id is None:
        trend_query = trend_query.where(Trend.topic_id.is_(None))
    else:
        trend_query = trend_query.where(Trend.topic_id == topic_id)
    trends = (await db.execute(
        trend_query.order_by(Trend.generated_at.desc()).limit(10)
    )).scalars().all()
    return [TrendResponse(
        id=t.id, topic_id=t.topic_id, topic_name=None, trend_type=t.trend_type, entity_id=t.entity_id,
        period_start=t.period_start, period_end=t.period_end,
        narrative=t.narrative, sentiment_score=t.sentiment_score,
        top_themes=json.loads(t.top_themes or "[]"),
        item_count=t.item_count, generated_at=t.generated_at,
    ) for t in trends]

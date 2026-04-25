import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.topic import Topic
from app.models.trend import Trend
from app.models.vendor import Vendor
from app.models.vertical import Vertical
from app.schemas.trend import TrendResponse

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/overall", response_model=TrendResponse | None)
async def get_overall_trend(topic_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Trend).where(Trend.trend_type == "overall")
    if topic_id is None:
        query = query.where(Trend.topic_id.is_(None))
    else:
        query = query.where(Trend.topic_id == topic_id)
    trend = (await db.execute(query.order_by(Trend.generated_at.desc()))).scalar_one_or_none()
    if not trend:
        return None
    topic = None
    if trend.topic_id is not None:
        topic = (await db.execute(select(Topic).where(Topic.id == trend.topic_id))).scalar_one_or_none()
    return TrendResponse(
        id=trend.id, topic_id=trend.topic_id, topic_name=topic.name if topic else None, trend_type=trend.trend_type, entity_id=trend.entity_id,
        period_start=trend.period_start, period_end=trend.period_end,
        narrative=trend.narrative, sentiment_score=trend.sentiment_score,
        top_themes=json.loads(trend.top_themes or "[]"),
        item_count=trend.item_count, generated_at=trend.generated_at,
    )


@router.get("/vendors")
async def get_vendor_trends(limit: int = Query(10, ge=1, le=50), topic_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Trend).where(Trend.trend_type == "vendor")
    if topic_id is None:
        query = query.where(Trend.topic_id.is_(None))
    else:
        query = query.where(Trend.topic_id == topic_id)
    trends = (await db.execute(
        query.order_by(Trend.generated_at.desc()).limit(limit)
    )).scalars().all()
    result = []
    for t in trends:
        vendor = (await db.execute(select(Vendor).where(Vendor.id == t.entity_id))).scalar_one_or_none()
        topic = None
        if t.topic_id is not None:
            topic = (await db.execute(select(Topic).where(Topic.id == t.topic_id))).scalar_one_or_none()
        result.append({
            "trend": TrendResponse(
                id=t.id, topic_id=t.topic_id, topic_name=topic.name if topic else None, trend_type=t.trend_type, entity_id=t.entity_id,
                period_start=t.period_start, period_end=t.period_end,
                narrative=t.narrative, sentiment_score=t.sentiment_score,
                top_themes=json.loads(t.top_themes or "[]"),
                item_count=t.item_count, generated_at=t.generated_at,
            ).model_dump(),
            "vendor": {"id": vendor.id, "name": vendor.name, "slug": vendor.slug} if vendor else None,
        })
    return {"trends": result}


@router.get("/verticals")
async def get_vertical_trends(limit: int = Query(10, ge=1, le=50), topic_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Trend).where(Trend.trend_type == "vertical")
    if topic_id is None:
        query = query.where(Trend.topic_id.is_(None))
    else:
        query = query.where(Trend.topic_id == topic_id)
    trends = (await db.execute(
        query.order_by(Trend.generated_at.desc()).limit(limit)
    )).scalars().all()
    result = []
    for t in trends:
        vertical = (await db.execute(select(Vertical).where(Vertical.id == t.entity_id))).scalar_one_or_none()
        topic = None
        if t.topic_id is not None:
            topic = (await db.execute(select(Topic).where(Topic.id == t.topic_id))).scalar_one_or_none()
        result.append({
            "trend": TrendResponse(
                id=t.id, topic_id=t.topic_id, topic_name=topic.name if topic else None, trend_type=t.trend_type, entity_id=t.entity_id,
                period_start=t.period_start, period_end=t.period_end,
                narrative=t.narrative, sentiment_score=t.sentiment_score,
                top_themes=json.loads(t.top_themes or "[]"),
                item_count=t.item_count, generated_at=t.generated_at,
            ).model_dump(),
            "vertical": {"id": vertical.id, "name": vertical.name, "slug": vertical.slug} if vertical else None,
        })
    return {"trends": result}

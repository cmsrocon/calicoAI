import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news_item import NewsItem, NewsItemVendor, NewsItemVertical
from app.models.trend import Trend
from app.models.vendor import Vendor
from app.models.vertical import Vertical
from app.services.llm_service import LLMService
from app.utils.date_utils import utcnow


async def update_trends(db: AsyncSession, llm: LLMService, days: int = 7) -> None:
    period_end = utcnow()
    period_start = period_end - timedelta(days=days)

    result = await db.execute(
        select(NewsItem).where(
            NewsItem.ingested_at >= period_start,
            NewsItem.is_processed == True,
        )
    )
    all_items = result.scalars().all()
    if not all_items:
        return

    # Vendor trends
    vendors = (await db.execute(select(Vendor).where(Vendor.is_active == True))).scalars().all()
    for vendor in vendors:
        vendor_item_ids = (await db.execute(
            select(NewsItemVendor.news_item_id).where(NewsItemVendor.vendor_id == vendor.id)
        )).scalars().all()
        vendor_items = [i for i in all_items if i.id in set(vendor_item_ids)]
        if len(vendor_items) < 2:
            continue
        item_dicts = [{"headline": i.headline, "summary": i.summary or "", "importance_rank": i.importance_rank or 5} for i in vendor_items]
        try:
            trend_data = await llm.analyze_trends(vendor.name, item_dicts)
            await _upsert_trend(db, "vendor", vendor.id, period_start, period_end, trend_data, len(vendor_items))
        except Exception:
            pass

    # Vertical trends
    verticals = (await db.execute(select(Vertical))).scalars().all()
    for vertical in verticals:
        vert_item_ids = (await db.execute(
            select(NewsItemVertical.news_item_id).where(NewsItemVertical.vertical_id == vertical.id)
        )).scalars().all()
        vert_items = [i for i in all_items if i.id in set(vert_item_ids)]
        if len(vert_items) < 2:
            continue
        item_dicts = [{"headline": i.headline, "summary": i.summary or "", "importance_rank": i.importance_rank or 5} for i in vert_items]
        try:
            trend_data = await llm.analyze_trends(vertical.name, item_dicts)
            await _upsert_trend(db, "vertical", vertical.id, period_start, period_end, trend_data, len(vert_items))
        except Exception:
            pass

    # Overall trend
    top_items = sorted(all_items, key=lambda i: i.importance_rank or 0, reverse=True)[:40]
    item_dicts = [{"headline": i.headline, "summary": i.summary or "", "importance_rank": i.importance_rank or 5} for i in top_items]
    try:
        trend_data = await llm.analyze_overall_trends(item_dicts)
        await _upsert_trend(db, "overall", None, period_start, period_end, trend_data, len(all_items))
    except Exception:
        pass

    await db.commit()


async def _upsert_trend(db: AsyncSession, trend_type: str, entity_id: int | None,
                         period_start: datetime, period_end: datetime,
                         data: dict, item_count: int) -> None:
    result = await db.execute(
        select(Trend).where(
            Trend.trend_type == trend_type,
            Trend.entity_id == entity_id,
            Trend.period_start == period_start,
        )
    )
    trend = result.scalar_one_or_none()
    if trend:
        trend.narrative = data.get("narrative")
        trend.sentiment_score = data.get("sentiment_score")
        trend.top_themes = json.dumps(data.get("top_themes", []))
        trend.item_count = item_count
        trend.period_end = period_end
        trend.generated_at = utcnow()
    else:
        db.add(Trend(
            trend_type=trend_type,
            entity_id=entity_id,
            period_start=period_start,
            period_end=period_end,
            narrative=data.get("narrative"),
            sentiment_score=data.get("sentiment_score"),
            top_themes=json.dumps(data.get("top_themes", [])),
            item_count=item_count,
            generated_at=utcnow(),
        ))

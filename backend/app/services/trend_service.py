import json
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news_item import NewsItem, NewsItemVendor, NewsItemVertical
from app.models.topic import Topic
from app.models.trend import Trend
from app.models.vendor import Vendor
from app.models.vertical import Vertical
from app.services.llm_service import LLMService
from app.utils.date_utils import utcnow


async def update_trends(db: AsyncSession, llm: LLMService, days: int = 7) -> None:
    period_end = utcnow()
    period_start = period_end - timedelta(days=days)

    all_items = (await db.execute(
        select(NewsItem).where(
            NewsItem.ingested_at >= period_start,
            NewsItem.is_processed == True,
        )
    )).scalars().all()
    if not all_items:
        return

    topics = (await db.execute(select(Topic).order_by(Topic.name.asc()))).scalars().all()
    topic_map = {topic.id: topic for topic in topics}
    topic_scopes: list[tuple[int | None, str | None, list[NewsItem]]] = [
        (None, None, all_items),
    ]
    for topic in topics:
        scoped_items = [item for item in all_items if item.topic_id == topic.id]
        if scoped_items:
            topic_scopes.append((topic.id, topic.name, scoped_items))

    vendor_links = (await db.execute(select(NewsItemVendor.news_item_id, NewsItemVendor.vendor_id))).all()
    vertical_links = (await db.execute(select(NewsItemVertical.news_item_id, NewsItemVertical.vertical_id))).all()
    vendor_map: dict[int, set[int]] = {}
    vertical_map: dict[int, set[int]] = {}
    for news_item_id, vendor_id in vendor_links:
        vendor_map.setdefault(vendor_id, set()).add(news_item_id)
    for news_item_id, vertical_id in vertical_links:
        vertical_map.setdefault(vertical_id, set()).add(news_item_id)

    vendors = (await db.execute(select(Vendor).where(Vendor.is_active == True))).scalars().all()
    verticals = (await db.execute(select(Vertical))).scalars().all()

    for scoped_topic_id, scoped_topic_name, scoped_items in topic_scopes:
        scoped_ids = {item.id for item in scoped_items}

        for vendor in vendors:
            entity_items = [item for item in scoped_items if item.id in vendor_map.get(vendor.id, set())]
            if len(entity_items) < 2:
                continue
            item_dicts = [
                {"headline": item.headline, "summary": item.summary or "", "importance_rank": item.importance_rank or 5}
                for item in entity_items
            ]
            try:
                trend_data = await llm.analyze_trends(vendor.name, item_dicts, scoped_topic_name)
                await _upsert_trend(
                    db,
                    scoped_topic_id,
                    "vendor",
                    vendor.id,
                    period_start,
                    period_end,
                    trend_data,
                    len(entity_items),
                )
            except Exception:
                pass

        for vertical in verticals:
            theme_items = [item for item in scoped_items if item.id in vertical_map.get(vertical.id, set())]
            if len(theme_items) < 2:
                continue
            item_dicts = [
                {"headline": item.headline, "summary": item.summary or "", "importance_rank": item.importance_rank or 5}
                for item in theme_items
            ]
            try:
                trend_data = await llm.analyze_trends(vertical.name, item_dicts, scoped_topic_name)
                await _upsert_trend(
                    db,
                    scoped_topic_id,
                    "vertical",
                    vertical.id,
                    period_start,
                    period_end,
                    trend_data,
                    len(theme_items),
                )
            except Exception:
                pass

        top_items = sorted(scoped_items, key=lambda item: item.importance_rank or 0, reverse=True)[:40]
        item_dicts = [
            {"headline": item.headline, "summary": item.summary or "", "importance_rank": item.importance_rank or 5}
            for item in top_items
        ]
        try:
            trend_data = await llm.analyze_overall_trends(item_dicts, scoped_topic_name)
            await _upsert_trend(
                db,
                scoped_topic_id,
                "overall",
                None,
                period_start,
                period_end,
                trend_data,
                len(scoped_ids),
            )
        except Exception:
            pass

    await db.commit()


async def _upsert_trend(
    db: AsyncSession,
    topic_id: int | None,
    trend_type: str,
    entity_id: int | None,
    period_start: datetime,
    period_end: datetime,
    data: dict,
    item_count: int,
) -> None:
    result = await db.execute(
        select(Trend).where(
            Trend.topic_id == topic_id,
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
        return

    db.add(Trend(
        topic_id=topic_id,
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

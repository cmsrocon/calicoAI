import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.news_item import NewsItem, NewsItemVendor, NewsItemVertical
from app.models.source import Source
from app.models.vendor import Vendor
from app.models.vertical import Vertical
from app.schemas.news_item import NewsItemDetail, NewsItemSummary, NewsItemVendorInfo, NewsItemVerticalInfo, NewsListResponse

router = APIRouter(prefix="/news", tags=["news"])


async def _enrich_item(item: NewsItem, db: AsyncSession) -> dict:
    # Vendors
    vendor_rows = (await db.execute(
        select(NewsItemVendor, Vendor)
        .join(Vendor, NewsItemVendor.vendor_id == Vendor.id)
        .where(NewsItemVendor.news_item_id == item.id)
    )).all()
    vendors = [NewsItemVendorInfo(id=v.id, name=v.name, slug=v.slug, confidence=niv.confidence) for niv, v in vendor_rows]

    # Verticals
    vert_rows = (await db.execute(
        select(NewsItemVertical, Vertical)
        .join(Vertical, NewsItemVertical.vertical_id == Vertical.id)
        .where(NewsItemVertical.news_item_id == item.id)
    )).all()
    verticals = [NewsItemVerticalInfo(id=v.id, name=v.name, slug=v.slug, confidence=niv.confidence) for niv, v in vert_rows]

    # Source name
    source_name = None
    if item.source_id:
        src = (await db.execute(select(Source).where(Source.id == item.source_id))).scalar_one_or_none()
        source_name = src.name if src else None

    return dict(
        id=item.id, headline=item.headline, external_url=item.external_url,
        source_id=item.source_id, source_name=source_name,
        published_at=item.published_at, ingested_at=item.ingested_at,
        language=item.language, summary=item.summary, why_it_matters=item.why_it_matters,
        importance_rank=item.importance_rank, ai_relevance_score=item.ai_relevance_score,
        vendors=vendors, verticals=verticals,
        pros=json.loads(item.pros or "[]"),
        cons=json.loads(item.cons or "[]"),
        balanced_take=item.balanced_take, is_processed=item.is_processed,
        processing_error=item.processing_error,
    )


@router.get("", response_model=NewsListResponse)
async def list_news(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    vendor_id: int | None = None,
    vertical_id: int | None = None,
    source_id: int | None = None,
    language: str | None = None,
    min_importance: int | None = Query(None, ge=1, le=10),
    search: str | None = None,
    sort_by: str = Query("importance", pattern="^(importance|date)$"),
    db: AsyncSession = Depends(get_db),
):
    query = select(NewsItem)
    if date_from:
        query = query.where(NewsItem.ingested_at >= date_from)
    if date_to:
        query = query.where(NewsItem.ingested_at <= date_to)
    if source_id:
        query = query.where(NewsItem.source_id == source_id)
    if language:
        query = query.where(NewsItem.language == language)
    if min_importance:
        query = query.where(NewsItem.importance_rank >= min_importance)
    if search:
        query = query.where(
            NewsItem.headline.ilike(f"%{search}%") | NewsItem.summary.ilike(f"%{search}%")
        )
    if vendor_id:
        query = query.join(NewsItemVendor, NewsItemVendor.news_item_id == NewsItem.id).where(NewsItemVendor.vendor_id == vendor_id)
    if vertical_id:
        query = query.join(NewsItemVertical, NewsItemVertical.news_item_id == NewsItem.id).where(NewsItemVertical.vertical_id == vertical_id)

    if sort_by == "importance":
        query = query.order_by(NewsItem.importance_rank.desc().nullslast(), NewsItem.ingested_at.desc())
    else:
        query = query.order_by(NewsItem.ingested_at.desc())

    all_items = (await db.execute(query)).scalars().all()
    total = len(all_items)
    offset = (page - 1) * page_size
    page_items = all_items[offset:offset + page_size]

    enriched = []
    for item in page_items:
        d = await _enrich_item(item, db)
        enriched.append(NewsItemSummary(**{k: v for k, v in d.items() if k in NewsItemSummary.model_fields}))

    return NewsListResponse(items=enriched, total=total, page=page, page_size=page_size)


@router.get("/{item_id}", response_model=NewsItemDetail)
async def get_news_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = (await db.execute(select(NewsItem).where(NewsItem.id == item_id))).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
    d = await _enrich_item(item, db)
    return NewsItemDetail(**d)

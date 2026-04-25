from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.source import Source
from app.models.topic import Topic
from app.schemas.source import SourceCreate, SourceResponse, SourceTestResult, SourceUpdate
from app.services.scraper_service import test_source
from app.services.topic_service import get_topic
from app.utils.date_utils import utcnow

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
async def list_sources(topic_id: int | None = Query(None), db: AsyncSession = Depends(get_db)):
    query = select(Source, Topic).join(Topic, Topic.id == Source.topic_id)
    if topic_id is not None:
        query = query.where(Source.topic_id == topic_id)
    query = query.order_by(Topic.name, Source.name)
    rows = (await db.execute(query)).all()
    return [
        SourceResponse(
            id=source.id,
            topic_id=source.topic_id,
            topic_name=topic.name,
            url=source.url,
            name=source.name,
            feed_type=source.feed_type,
            is_active=source.is_active,
            trust_weight=source.trust_weight,
            css_selector=source.css_selector,
            last_fetched_at=source.last_fetched_at,
            last_error=source.last_error,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )
        for source, topic in rows
    ]


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(body: SourceCreate, db: AsyncSession = Depends(get_db)):
    topic = await get_topic(db, body.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    existing = (await db.execute(
        select(Source).where(Source.topic_id == body.topic_id, Source.url == body.url)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Source URL already exists for this topic")
    source = Source(**body.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return SourceResponse(
        id=source.id,
        topic_id=source.topic_id,
        topic_name=topic.name,
        url=source.url,
        name=source.name,
        feed_type=source.feed_type,
        is_active=source.is_active,
        trust_weight=source.trust_weight,
        css_selector=source.css_selector,
        last_fetched_at=source.last_fetched_at,
        last_error=source.last_error,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(source_id: int, body: SourceUpdate, db: AsyncSession = Depends(get_db)):
    source = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(source, field, value)
    source.updated_at = utcnow()
    await db.commit()
    await db.refresh(source)
    topic = await get_topic(db, source.topic_id)
    return SourceResponse(
        id=source.id,
        topic_id=source.topic_id,
        topic_name=topic.name if topic else None,
        url=source.url,
        name=source.name,
        feed_type=source.feed_type,
        is_active=source.is_active,
        trust_weight=source.trust_weight,
        css_selector=source.css_selector,
        last_fetched_at=source.last_fetched_at,
        last_error=source.last_error,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.delete("/{source_id}", status_code=204)
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    source = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.delete(source)
    await db.commit()


@router.post("/{source_id}/test", response_model=SourceTestResult)
async def test_source_endpoint(source_id: int, db: AsyncSession = Depends(get_db)):
    source = (await db.execute(select(Source).where(Source.id == source_id))).scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    count, sample, error = await test_source(source.url, source.feed_type, source.css_selector)
    return SourceTestResult(success=error is None, item_count=count, sample_title=sample, error=error)

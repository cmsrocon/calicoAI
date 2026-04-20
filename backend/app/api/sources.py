from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.source import Source
from app.schemas.source import SourceCreate, SourceResponse, SourceTestResult, SourceUpdate
from app.services.scraper_service import test_source
from app.utils.date_utils import utcnow

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
async def list_sources(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).order_by(Source.name))
    return result.scalars().all()


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(body: SourceCreate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(Source).where(Source.url == body.url))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Source URL already exists")
    source = Source(**body.model_dump())
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return source


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
    return source


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

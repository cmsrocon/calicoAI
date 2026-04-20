from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_db
from app.models.ingestion_run import IngestionRun
from app.schemas.ingestion import IngestionRunResponse, IngestionStatusResponse, TriggerResponse
from app.services import ingestion_service
from app.services.llm_service import get_llm_service

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.get("/status", response_model=IngestionStatusResponse)
async def get_status(db: AsyncSession = Depends(get_db)):
    last_run_row = (await db.execute(
        select(IngestionRun).order_by(IngestionRun.started_at.desc())
    )).scalar_one_or_none()
    last_run = IngestionRunResponse.model_validate(last_run_row) if last_run_row else None
    running = ingestion_service.is_running()
    progress = ingestion_service.get_progress() if running else {}
    return IngestionStatusResponse(
        last_run=last_run,
        next_run_at=None,
        is_running=running,
        current_stage=progress.get("stage") or None,
        current_stage_detail=progress.get("detail") or None,
        live_calls=progress.get("calls") if running else None,
        live_tokens_in=progress.get("tokens_in") if running else None,
        live_tokens_out=progress.get("tokens_out") if running else None,
        live_cost_usd=progress.get("estimated_cost_usd") if running else None,
    )


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_ingestion(background_tasks: BackgroundTasks):
    if ingestion_service.is_running():
        raise HTTPException(status_code=409, detail="Ingestion is already running")
    llm = get_llm_service()

    async def run_bg():
        async with async_session_factory() as db:
            await ingestion_service.run_ingestion(db, llm, triggered_by="manual")

    background_tasks.add_task(run_bg)
    return TriggerResponse(run_id=0, message="Ingestion started in background")


@router.get("/runs", response_model=dict)
async def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(IngestionRun).order_by(IngestionRun.started_at.desc())
    )).scalars().all()
    total = len(rows)
    offset = (page - 1) * page_size
    page_rows = rows[offset:offset + page_size]
    return {"runs": [IngestionRunResponse.model_validate(r).model_dump() for r in page_rows], "total": total}


@router.post("/retry-failed")
async def retry_failed(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    if ingestion_service.is_running():
        raise HTTPException(status_code=409, detail="Ingestion is already running")
    llm = get_llm_service()

    async def run_bg():
        async with async_session_factory() as session:
            await ingestion_service.run_ingestion(session, llm, triggered_by="retry")

    background_tasks.add_task(run_bg)
    return {"message": "Retry ingestion started"}

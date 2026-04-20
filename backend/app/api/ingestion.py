from datetime import datetime
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.settings import load_raw_settings
from app.database import async_session_factory, get_db
from app.models.ingestion_run import IngestionRun
from app.schemas.ingestion import IngestionRunResponse, IngestionStatusResponse, TriggerResponse
from app.services import ingestion_service
from app.services.llm_service import get_llm_service

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
logger = logging.getLogger(__name__)


def _validate_llm_settings(raw: dict[str, str]) -> None:
    provider = raw.get("llm_provider", "")
    model = (raw.get("llm_model") or "").strip()
    if not model:
        raise HTTPException(
            status_code=400,
            detail="No model is configured. Open Settings, choose a model, run Test connection, then try Refresh again.",
        )

    key_for_provider = {
        "anthropic": raw.get("anthropic_api_key", ""),
        "openai": raw.get("openai_api_key", ""),
        "minimax": raw.get("minimax_api_key", ""),
        "ollama": "local",
    }.get(provider, "")

    if provider != "ollama" and not key_for_provider:
        raise HTTPException(
            status_code=400,
            detail=f"No {provider} API key is configured. Open Settings, add a key, run Test connection, then try Refresh again.",
        )


async def _validate_trigger_request() -> None:
    async with async_session_factory() as db:
        raw = await load_raw_settings(db)
    _validate_llm_settings(raw)


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
        last_error=progress.get("last_error") or None,
        live_calls=progress.get("calls") if running else None,
        live_tokens_in=progress.get("tokens_in") if running else None,
        live_tokens_out=progress.get("tokens_out") if running else None,
        live_cost_usd=progress.get("estimated_cost_usd") if running else None,
    )


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_ingestion(background_tasks: BackgroundTasks):
    if ingestion_service.is_running():
        raise HTTPException(status_code=409, detail="Ingestion is already running")
    await _validate_trigger_request()
    llm = get_llm_service()

    async def run_bg():
        async with async_session_factory() as db:
            try:
                await ingestion_service.run_ingestion(db, llm, triggered_by="manual")
            except Exception:
                logger.exception("Manual ingestion task failed before progress state could be persisted")

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
async def retry_failed(background_tasks: BackgroundTasks):
    if ingestion_service.is_running():
        raise HTTPException(status_code=409, detail="Ingestion is already running")
    await _validate_trigger_request()
    llm = get_llm_service()

    async def run_bg():
        async with async_session_factory() as session:
            try:
                await ingestion_service.run_ingestion(session, llm, triggered_by="retry")
            except Exception:
                logger.exception("Retry ingestion task failed before progress state could be persisted")

    background_tasks.add_task(run_bg)
    return {"message": "Retry ingestion started"}

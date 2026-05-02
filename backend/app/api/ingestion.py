from datetime import datetime
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.settings import load_raw_settings
from app.database import async_session_factory, get_db
from app.models.ingestion_run import IngestionRun
from app.models.topic import Topic
from app.schemas.ingestion import IngestionRunResponse, IngestionStatusResponse, TriggerResponse
from app.services import ingestion_service
from app.services.auth_service import TokenQuotaExceededError, UserUsageTracker, require_admin_user
from app.services.llm_service import get_llm_service

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
logger = logging.getLogger(__name__)


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _serialize_last_run(row: IngestionRun | None) -> IngestionRunResponse | None:
    if row is None:
        return None
    try:
        return IngestionRunResponse.model_validate(row)
    except Exception:
        logger.exception("Failed to serialize ingestion run %s for status response", getattr(row, "id", "unknown"))
        return None


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
    running = ingestion_service.is_running()
    progress = ingestion_service.get_progress() if running else {}

    last_run = None
    try:
        last_run_row = (await db.execute(
            select(IngestionRun).order_by(IngestionRun.started_at.desc())
        )).scalar_one_or_none()
        last_run = _serialize_last_run(last_run_row)
    except SQLAlchemyError:
        logger.exception("Failed to query ingestion status while a refresh was active")

    return IngestionStatusResponse(
        last_run=last_run,
        next_run_at=None,
        is_running=running,
        current_stage=progress.get("stage") or None,
        current_stage_detail=progress.get("detail") or None,
        last_error=progress.get("last_error") or None,
        live_calls=_coerce_int(progress.get("calls")) if running else None,
        live_tokens_in=_coerce_int(progress.get("tokens_in")) if running else None,
        live_tokens_out=_coerce_int(progress.get("tokens_out")) if running else None,
        live_cost_usd=_coerce_float(progress.get("estimated_cost_usd")) if running else None,
    )


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_ingestion(
    background_tasks: BackgroundTasks,
    topic_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_admin_user),
):
    if ingestion_service.should_reuse_active_run(topic_id):
        return TriggerResponse(run_id=0, message="A matching refresh is already in progress", reused_existing_run=True)
    if ingestion_service.is_running():
        raise HTTPException(status_code=409, detail="A refresh is already running for a different scope")
    await _validate_trigger_request()
    topic_name: str | None = None

    if topic_id is not None:
        topic = (await db.execute(select(Topic).where(Topic.id == topic_id))).scalar_one_or_none()
        if topic is None:
            raise HTTPException(status_code=404, detail="Topic not found")
        topic_name = topic.name

    cached_run = await ingestion_service.get_recent_matching_run(db, topic_id)
    if cached_run is not None:
        return TriggerResponse(
            run_id=cached_run.id,
            message="Using the most recent refresh result for this scope",
            reused_existing_run=True,
        )

    llm = get_llm_service().fork(UserUsageTracker(user.id, f"ingestion.trigger:{topic_id or 'all'}"))

    async def run_bg():
        async with async_session_factory() as db:
            try:
                await ingestion_service.run_ingestion(db, llm, triggered_by="manual", topic_id=topic_id, user_id=user.id)
            except TokenQuotaExceededError as exc:
                logger.warning("Manual ingestion stopped because the user's token quota was exceeded: %s", exc)
            except Exception:
                logger.exception("Manual ingestion task failed before progress state could be persisted")

    background_tasks.add_task(run_bg)
    message = (
        f"Ingestion started in background for topic '{topic_name}'"
        if topic_name
        else "Ingestion started in background for all topics"
    )
    return TriggerResponse(run_id=0, message=message)


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
async def retry_failed(background_tasks: BackgroundTasks, user=Depends(require_admin_user)):
    if ingestion_service.is_running():
        raise HTTPException(status_code=409, detail="Ingestion is already running")
    await _validate_trigger_request()
    llm = get_llm_service().fork(UserUsageTracker(user.id, "ingestion.retry_failed"))

    async def run_bg():
        async with async_session_factory() as session:
            try:
                await ingestion_service.run_ingestion(session, llm, triggered_by="retry", user_id=user.id)
            except Exception:
                logger.exception("Retry ingestion task failed before progress state could be persisted")

    background_tasks.add_task(run_bg)
    return {"message": "Retry ingestion started"}

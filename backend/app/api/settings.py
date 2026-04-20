import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.app_setting import AppSetting
from app.services.llm_service import LLMService, get_llm_service, set_llm_service
from app.utils.date_utils import utcnow

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "llm_provider": "anthropic",
    "llm_model": "claude-sonnet-4-6",
    "llm_max_tokens": "1500",
    "schedule_hour": "6",
    "schedule_minute": "0",
}


async def load_settings(db: AsyncSession) -> dict[str, str]:
    rows = (await db.execute(select(AppSetting))).scalars().all()
    result = dict(DEFAULT_SETTINGS)
    result.update({r.key: r.value for r in rows})
    return result


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await load_settings(db)


@router.patch("")
async def update_settings(body: dict, db: AsyncSession = Depends(get_db)):
    for key, value in body.items():
        row = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
        if row:
            row.value = str(value)
            row.updated_at = utcnow()
        else:
            db.add(AppSetting(key=key, value=str(value)))
    await db.commit()
    current = await load_settings(db)
    # Hot-reload LLM service
    from app.config import settings as app_config
    new_llm = LLMService(
        provider=current["llm_provider"],
        model=current["llm_model"],
        anthropic_api_key=app_config.anthropic_api_key,
        openai_api_key=app_config.openai_api_key,
        minimax_api_key=app_config.minimax_api_key,
        # UI-saved ollama_base_url takes priority over env var
        ollama_base_url=current.get("ollama_base_url") or app_config.ollama_base_url,
    )
    set_llm_service(new_llm)
    return current


@router.get("/health")
async def settings_health(db: AsyncSession = Depends(get_db)):
    current = await load_settings(db)
    llm = get_llm_service()
    start = time.monotonic()
    try:
        await llm.complete("You are a test assistant.", "Reply with the word OK only.", max_tokens=10, temperature=0)
        latency_ms = int((time.monotonic() - start) * 1000)
        return {"status": "ok", "provider": current["llm_provider"], "model": current["llm_model"], "latency_ms": latency_ms}
    except Exception as e:
        return {"status": "error", "error": str(e), "provider": current["llm_provider"], "model": current["llm_model"]}

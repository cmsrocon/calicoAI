import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.router import api_router
from app.config import settings
from app.database import async_session_factory, init_db
from app.models import Source
from app.models.app_setting import AppSetting
from app.scheduler import start_scheduler
from app.services.llm_service import LLMService, set_llm_service
from app.services.vertical_service import seed_verticals

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session_factory() as db:
        # Seed default sources
        seeds_path = Path(__file__).parent.parent / "seeds" / "default_sources.json"
        if seeds_path.exists():
            sources_data = json.loads(seeds_path.read_text())
            for s in sources_data:
                existing = (await db.execute(select(Source).where(Source.url == s["url"]))).scalar_one_or_none()
                if not existing:
                    db.add(Source(**s))
            await db.commit()

        # Seed verticals
        await seed_verticals(db)

        # Load LLM settings
        rows = (await db.execute(select(AppSetting))).scalars().all()
        settings_map = {r.key: r.value for r in rows}
        provider = settings_map.get("llm_provider", settings.default_llm_provider)
        model = settings_map.get("llm_model", settings.default_llm_model)
        llm = LLMService(
            provider=provider,
            model=model,
            anthropic_api_key=settings.anthropic_api_key,
            openai_api_key=settings.openai_api_key,
            minimax_api_key=settings.minimax_api_key,
            ollama_base_url=settings.ollama_base_url,
        )
        set_llm_service(llm)
        logger.info(f"LLM initialized: provider={provider} model={model}")

        # Start scheduler
        hour = int(settings_map.get("schedule_hour", "6"))
        minute = int(settings_map.get("schedule_minute", "0"))
        start_scheduler(hour=hour, minute=minute)

    yield

    from app.scheduler import stop_scheduler
    stop_scheduler()


app = FastAPI(title="GingerAI", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

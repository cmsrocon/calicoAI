import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.database import async_session_factory, init_db
from app.config import settings
from app.middleware import SecurityMiddleware
from app.scheduler import start_scheduler
from app.services.llm_service import set_llm_service
from app.services.auth_service import ensure_superadmin
from app.services.topic_service import ensure_default_topic, seed_default_topic_sources

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await ensure_superadmin()
    async with async_session_factory() as db:
        # Ensure the original AI monitor becomes the default topic, then attach the curated starter sources to it.
        default_topic = await ensure_default_topic(db)
        await seed_default_topic_sources(db, default_topic.id)

        # Load LLM settings (keys from DB take priority over .env)
        from app.api.settings import load_raw_settings, _build_llm
        raw = await load_raw_settings(db)
        llm = _build_llm(raw)
        set_llm_service(llm)
        logger.info(f"LLM initialized: provider={raw['llm_provider']} model={raw['llm_model']}")

        # Start scheduler
        hour = int(raw.get("schedule_hour", "6"))
        minute = int(raw.get("schedule_minute", "0"))
        start_scheduler(hour=hour, minute=minute)

    yield

    from app.scheduler import stop_scheduler
    stop_scheduler()


app = FastAPI(title="calicoAI", version="1.1.0", lifespan=lifespan)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list() or ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token"],
)
app.add_middleware(SecurityMiddleware)

app.include_router(api_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.1.0"}

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.router import api_router
from app.database import async_session_factory, init_db
from app.models import Source
from app.scheduler import start_scheduler
from app.services.llm_service import set_llm_service
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

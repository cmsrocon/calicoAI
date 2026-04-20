from fastapi import APIRouter

from app.api.ingestion import router as ingestion_router
from app.api.news import router as news_router
from app.api.settings import router as settings_router
from app.api.sources import router as sources_router
from app.api.trends import router as trends_router
from app.api.vendors import router as vendors_router
from app.api.verticals import router as verticals_router

api_router = APIRouter(prefix="/api")

api_router.include_router(news_router)
api_router.include_router(vendors_router)
api_router.include_router(verticals_router)
api_router.include_router(trends_router)
api_router.include_router(sources_router)
api_router.include_router(ingestion_router)
api_router.include_router(settings_router)

from fastapi import APIRouter, Depends

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.graph import router as graph_router
from app.api.ingestion import router as ingestion_router
from app.api.news import router as news_router
from app.api.settings import router as settings_router
from app.api.sources import router as sources_router
from app.api.topics import router as topics_router
from app.api.trends import router as trends_router
from app.api.vendors import router as vendors_router
from app.api.verticals import router as verticals_router
from app.services.auth_service import get_current_active_user

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(admin_router)
protected = [Depends(get_current_active_user)]

api_router.include_router(news_router, dependencies=protected)
api_router.include_router(topics_router, dependencies=protected)
api_router.include_router(vendors_router, dependencies=protected)
api_router.include_router(verticals_router, dependencies=protected)
api_router.include_router(trends_router, dependencies=protected)
api_router.include_router(graph_router, dependencies=protected)
api_router.include_router(sources_router, dependencies=protected)
api_router.include_router(ingestion_router, dependencies=protected)
api_router.include_router(settings_router, dependencies=protected)

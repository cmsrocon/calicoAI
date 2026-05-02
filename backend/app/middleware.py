from fastapi import Request
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.database import async_session_factory
from app.models.user_session import UserSession
from app.security import hash_token
from app.services.auth_service import (
    AUTH_ACTIVITY_EXCLUDE_PATHS,
    CSRF_COOKIE_NAME,
    REQUEST_ACTIVITY_EXCLUDE_PREFIXES,
    SESSION_COOKIE_NAME,
    SESSION_TOUCH_INTERVAL_SECONDS,
    record_activity,
)
from app.utils.date_utils import utcnow


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.auth_user_id = None
        request.state.auth_session_id = None

        session_token = request.cookies.get(SESSION_COOKIE_NAME)
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        csrf_header = request.headers.get("x-csrf-token")
        response = None

        if session_token:
            async with async_session_factory() as db:
                session = (await db.execute(
                    select(UserSession).where(UserSession.token_hash == hash_token(session_token))
                )).scalar_one_or_none()
                if session and session.revoked_at is None and session.expires_at > utcnow():
                    idle_age = (utcnow() - session.last_seen_at).total_seconds()
                    max_idle = settings.session_idle_timeout_minutes * 60
                    if idle_age <= max_idle:
                        request.state.auth_user_id = session.user_id
                        request.state.auth_session_id = session.id
                        if request.method not in {"GET", "HEAD", "OPTIONS"}:
                            if not csrf_cookie or not csrf_header or hash_token(csrf_header) != session.csrf_token_hash:
                                return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)
                        if idle_age >= SESSION_TOUCH_INTERVAL_SECONDS:
                            session.last_seen_at = utcnow()
                            await db.commit()
                    else:
                        session.revoked_at = utcnow()
                        await db.commit()

        response = await call_next(request)

        if request.state.auth_user_id and request.url.path not in AUTH_ACTIVITY_EXCLUDE_PATHS and not request.url.path.startswith(REQUEST_ACTIVITY_EXCLUDE_PREFIXES):
            await record_activity(
                request.state.auth_user_id,
                "request",
                request.method,
                request.url.path,
                response.status_code,
                request,
            )

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

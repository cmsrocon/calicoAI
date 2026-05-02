import json
from datetime import timedelta

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory, get_db
from app.models.token_usage_ledger import TokenUsageLedger
from app.models.user import User
from app.models.user_activity import UserActivity
from app.models.user_session import UserSession
from app.security import generate_csrf_token, generate_session_token, hash_password, hash_token, verify_password
from app.utils.date_utils import utcnow

SESSION_COOKIE_NAME = "calico_session"
CSRF_COOKIE_NAME = "calico_csrf"
SESSION_TOUCH_INTERVAL_SECONDS = 300
AUTH_ACTIVITY_EXCLUDE_PATHS = {"/api/auth/me"}
REQUEST_ACTIVITY_EXCLUDE_PREFIXES = ("/api/health",)


class TokenQuotaExceededError(RuntimeError):
    pass


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


def _same_site_value() -> str:
    return settings.session_cookie_same_site.lower()


def _cookie_secure() -> bool:
    return settings.require_https_cookies


def _json_details(details: dict | None) -> str | None:
    if not details:
        return None
    return json.dumps(details, default=str)


async def record_activity(
    user_id: int | None,
    action: str,
    method: str,
    path: str,
    status_code: int,
    request: Request | None = None,
    details: dict | None = None,
) -> None:
    async with async_session_factory() as db:
        db.add(UserActivity(
            user_id=user_id,
            action=action,
            method=method,
            path=path,
            status_code=status_code,
            ip_address=_client_ip(request) if request else None,
            user_agent=request.headers.get("user-agent")[:500] if request else None,
            details_json=_json_details(details),
            created_at=utcnow(),
        ))
        await db.commit()


async def get_token_usage_summary(db: AsyncSession, user: User) -> dict:
    window_start = utcnow() - timedelta(days=settings.token_quota_window_days)
    used = (await db.execute(
        select(func.coalesce(func.sum(TokenUsageLedger.tokens_in + TokenUsageLedger.tokens_out), 0))
        .where(TokenUsageLedger.user_id == user.id, TokenUsageLedger.created_at >= window_start)
    )).scalar_one()
    remaining = None if user.monthly_token_limit is None else max(user.monthly_token_limit - int(used), 0)
    return {
        "used_tokens": int(used),
        "monthly_token_limit": user.monthly_token_limit,
        "remaining_tokens": remaining,
        "window_days": settings.token_quota_window_days,
    }


async def serialize_user(db: AsyncSession, user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "last_login_at": user.last_login_at,
        "quota": await get_token_usage_summary(db, user),
    }


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = (await db.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def apply_session_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_same_site_value(),
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=_cookie_secure(),
        samesite=_same_site_value(),
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    for cookie_name, httponly in ((SESSION_COOKIE_NAME, True), (CSRF_COOKIE_NAME, False)):
        response.delete_cookie(
            key=cookie_name,
            httponly=httponly,
            secure=_cookie_secure(),
            samesite=_same_site_value(),
            path="/",
        )


async def create_session(db: AsyncSession, user: User, request: Request) -> tuple[str, str]:
    session_token = generate_session_token()
    csrf_token = generate_csrf_token()
    now = utcnow()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(session_token),
        csrf_token_hash=hash_token(csrf_token),
        ip_address=_client_ip(request),
        user_agent=(request.headers.get("user-agent") or "")[:500] or None,
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
    )
    user.last_login_at = now
    db.add(session)
    await db.commit()
    return session_token, csrf_token


async def revoke_session(db: AsyncSession, session_id: int) -> None:
    session = (await db.execute(select(UserSession).where(UserSession.id == session_id))).scalar_one_or_none()
    if not session or session.revoked_at is not None:
        return
    session.revoked_at = utcnow()
    await db.commit()


async def get_current_active_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    user_id = getattr(request.state, "auth_user_id", None)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


async def require_admin_user(user: User = Depends(get_current_active_user)) -> User:
    if user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def require_superadmin_user(user: User = Depends(get_current_active_user)) -> User:
    if user.role != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin access required")
    return user


class UserUsageTracker:
    def __init__(self, user_id: int, action: str):
        self.user_id = user_id
        self.action = action

    async def before_call(self, max_tokens: int) -> None:
        async with async_session_factory() as db:
            user = (await db.execute(select(User).where(User.id == self.user_id))).scalar_one_or_none()
            if not user or not user.is_active:
                raise TokenQuotaExceededError("User is inactive")
            if user.monthly_token_limit is None:
                return
            summary = await get_token_usage_summary(db, user)
            remaining = summary["remaining_tokens"]
            if remaining is not None and remaining < max_tokens:
                raise TokenQuotaExceededError(
                    f"Token quota exceeded. Remaining tokens: {remaining}. Required for next call: {max_tokens}."
                )

    async def record_call(self, model: str, tokens_in: int, tokens_out: int, estimated_cost_usd: float) -> None:
        async with async_session_factory() as db:
            db.add(TokenUsageLedger(
                user_id=self.user_id,
                action=self.action,
                model=model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                estimated_cost_usd=estimated_cost_usd,
                created_at=utcnow(),
            ))
            await db.commit()


async def ensure_superadmin() -> None:
    email = settings.superadmin_email.strip().lower()
    password = settings.superadmin_password
    full_name = settings.superadmin_name.strip()
    if not email or not password or not full_name:
        if settings.environment == "production":
            raise RuntimeError("Production requires SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD, and SUPERADMIN_NAME.")
        return

    async with async_session_factory() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user:
            changed = False
            if user.role != "superadmin":
                user.role = "superadmin"
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if changed:
                user.updated_at = utcnow()
                await db.commit()
            return

        db.add(User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role="superadmin",
            is_active=True,
            created_at=utcnow(),
            updated_at=utcnow(),
        ))
        await db.commit()

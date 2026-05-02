import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.user_activity import UserActivity
from app.schemas.admin import (
    AdminUserCreateRequest,
    AdminUserResponse,
    AdminUserUpdateRequest,
    UserActivityResponse,
)
from app.security import hash_password
from app.services.auth_service import get_token_usage_summary, record_activity, require_superadmin_user
from app.utils.date_utils import utcnow

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(db: AsyncSession = Depends(get_db), user=Depends(require_superadmin_user)):
    rows = (await db.execute(select(User).order_by(User.role.desc(), User.email.asc()))).scalars().all()
    return [
        AdminUserResponse(
            id=row.id,
            email=row.email,
            full_name=row.full_name,
            role=row.role,
            is_active=row.is_active,
            created_at=row.created_at,
            updated_at=row.updated_at,
            last_login_at=row.last_login_at,
            quota=await get_token_usage_summary(db, row),
        )
        for row in rows
    ]


@router.post("/users", response_model=AdminUserResponse, status_code=201)
async def create_user(
    body: AdminUserCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor=Depends(require_superadmin_user),
):
    email = body.email.strip().lower()
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User email already exists")
    user = User(
        email=email,
        full_name=body.full_name.strip(),
        password_hash=hash_password(body.password),
        role=body.role,
        is_active=True,
        monthly_token_limit=body.monthly_token_limit,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    await record_activity(actor.id, "admin.user_created", request.method, request.url.path, 201, request, {"user_id": user.id})
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        quota=await get_token_usage_summary(db, user),
    )


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    body: AdminUserUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor=Depends(require_superadmin_user),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == actor.id and body.is_active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own superadmin account")
    if user.id == actor.id and body.role and body.role != "superadmin":
        raise HTTPException(status_code=400, detail="You cannot remove your own superadmin role")

    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.clear_monthly_token_limit:
        user.monthly_token_limit = None
    elif body.monthly_token_limit is not None:
        user.monthly_token_limit = body.monthly_token_limit
    user.updated_at = utcnow()
    await db.commit()
    await db.refresh(user)
    await record_activity(actor.id, "admin.user_updated", request.method, request.url.path, 200, request, {"user_id": user.id})
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        quota=await get_token_usage_summary(db, user),
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor=Depends(require_superadmin_user),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == actor.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own superadmin account")
    await db.delete(user)
    await db.commit()
    await record_activity(actor.id, "admin.user_deleted", request.method, request.url.path, 204, request, {"user_id": user_id})


@router.get("/activity", response_model=list[UserActivityResponse])
async def list_activity(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_superadmin_user),
):
    rows = (await db.execute(
        select(UserActivity, User.email)
        .outerjoin(User, User.id == UserActivity.user_id)
        .order_by(UserActivity.created_at.desc())
        .limit(limit)
    )).all()
    return [
        UserActivityResponse(
            id=activity.id,
            user_id=activity.user_id,
            user_email=email,
            action=activity.action,
            method=activity.method,
            path=activity.path,
            status_code=activity.status_code,
            ip_address=activity.ip_address,
            user_agent=activity.user_agent,
            details=json.loads(activity.details_json) if activity.details_json else None,
            created_at=activity.created_at,
        )
        for activity, email in rows
    ]

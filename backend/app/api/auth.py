from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import ChangePasswordRequest, CurrentUserResponse, LoginRequest
from app.security import hash_password, verify_password
from app.services.auth_service import (
    apply_session_cookies,
    authenticate_user,
    clear_session_cookies,
    create_session,
    get_current_active_user,
    record_activity,
    revoke_session,
    serialize_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=CurrentUserResponse)
async def login(body: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.email, body.password)
    if user is None:
        await record_activity(None, "auth.login_failed", request.method, request.url.path, 401, request, {"email": body.email})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    session_token, csrf_token = await create_session(db, user, request)
    apply_session_cookies(response, session_token, csrf_token)
    await record_activity(user.id, "auth.login", request.method, request.url.path, 200, request)
    return CurrentUserResponse(**await serialize_user(db, user))


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_active_user),
):
    session_id = getattr(request.state, "auth_session_id", None)
    if session_id is not None:
        await revoke_session(db, session_id)
    clear_session_cookies(response)
    await record_activity(user.id, "auth.logout", request.method, request.url.path, 200, request)
    return {"message": "Logged out"}


@router.get("/me", response_model=CurrentUserResponse)
async def me(db: AsyncSession = Depends(get_db), user=Depends(get_current_active_user)):
    return CurrentUserResponse(**await serialize_user(db, user))


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_active_user),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    await record_activity(user.id, "auth.change_password", request.method, request.url.path, 200, request)
    return {"message": "Password updated"}

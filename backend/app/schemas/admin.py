from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.auth import UserQuotaSummary


class AdminUserCreateRequest(BaseModel):
    email: str
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=12, max_length=256)
    role: str = Field(pattern="^(user|admin|superadmin)$")
    monthly_token_limit: int | None = Field(default=None, ge=1)


class AdminUserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    password: str | None = Field(default=None, min_length=12, max_length=256)
    role: str | None = Field(default=None, pattern="^(user|admin|superadmin)$")
    is_active: bool | None = None
    monthly_token_limit: int | None = Field(default=None, ge=1)
    clear_monthly_token_limit: bool = False


class AdminUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    quota: UserQuotaSummary


class UserActivityResponse(BaseModel):
    id: int
    user_id: int | None = None
    user_email: str | None = None
    action: str
    method: str
    path: str
    status_code: int
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict | None = None
    created_at: datetime

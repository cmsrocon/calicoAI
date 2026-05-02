from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)


class UserQuotaSummary(BaseModel):
    used_tokens: int
    monthly_token_limit: int | None = None
    remaining_tokens: int | None = None
    window_days: int


class CurrentUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None = None
    quota: UserQuotaSummary

from datetime import datetime

from pydantic import BaseModel


class VendorResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    slug: str
    description: str | None = None
    aliases: list[str] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime
    news_count: int = 0


class VendorSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    slug: str
    description: str | None = None
    news_count: int = 0

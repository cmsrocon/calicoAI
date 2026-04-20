from datetime import datetime

from pydantic import BaseModel


class VerticalResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    slug: str
    description: str | None = None
    icon_name: str | None = None
    news_count: int = 0


class VerticalSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    slug: str
    icon_name: str | None = None
    news_count: int = 0

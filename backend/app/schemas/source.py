from datetime import datetime

from pydantic import BaseModel, HttpUrl


class SourceBase(BaseModel):
    url: str
    name: str
    feed_type: str = "rss"
    is_active: bool = True
    trust_weight: float = 1.0
    css_selector: str | None = None


class SourceCreate(SourceBase):
    pass


class SourceUpdate(BaseModel):
    name: str | None = None
    feed_type: str | None = None
    is_active: bool | None = None
    trust_weight: float | None = None
    css_selector: str | None = None


class SourceResponse(SourceBase):
    model_config = {"from_attributes": True}

    id: int
    last_fetched_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class SourceTestResult(BaseModel):
    success: bool
    item_count: int
    sample_title: str | None = None
    error: str | None = None

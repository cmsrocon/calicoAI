import json
from datetime import datetime

from pydantic import BaseModel, field_validator


class NewsItemVendorInfo(BaseModel):
    id: int
    name: str
    slug: str
    confidence: float


class NewsItemVerticalInfo(BaseModel):
    id: int
    name: str
    slug: str
    confidence: float


class NewsItemSummary(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    headline: str
    external_url: str
    source_id: int | None = None
    source_name: str | None = None
    published_at: datetime | None = None
    ingested_at: datetime
    language: str
    summary: str | None = None
    why_it_matters: str | None = None
    importance_rank: int | None = None
    ai_relevance_score: float | None = None
    vendors: list[NewsItemVendorInfo] = []
    verticals: list[NewsItemVerticalInfo] = []


class NewsItemDetail(NewsItemSummary):
    pros: list[str] = []
    cons: list[str] = []
    balanced_take: str | None = None
    is_processed: bool
    trust_weight: float | None = None


class NewsListResponse(BaseModel):
    items: list[NewsItemSummary]
    total: int
    page: int
    page_size: int

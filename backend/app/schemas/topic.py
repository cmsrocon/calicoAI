from datetime import datetime

from pydantic import BaseModel


class TopicCreate(BaseModel):
    name: str
    description: str | None = None


class TopicUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class TopicResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    slug: str
    description: str | None = None
    is_default: bool
    source_count: int = 0
    article_count: int = 0
    created_at: datetime
    updated_at: datetime


class TopicCreateResponse(BaseModel):
    topic: TopicResponse
    seeded_sources_count: int
    seed_status: str
    seed_message: str | None = None

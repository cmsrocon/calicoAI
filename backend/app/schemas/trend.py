from datetime import datetime

from pydantic import BaseModel


class TrendResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    topic_id: int | None = None
    topic_name: str | None = None
    trend_type: str
    entity_id: int | None = None
    period_start: datetime
    period_end: datetime
    narrative: str | None = None
    sentiment_score: float | None = None
    top_themes: list[str] = []
    item_count: int
    generated_at: datetime

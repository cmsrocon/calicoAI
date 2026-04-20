from datetime import datetime

from pydantic import BaseModel


class IngestionRunResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    items_fetched: int
    items_new: int
    items_duplicate: int
    triggered_by: str
    error_message: str | None = None


class IngestionStatusResponse(BaseModel):
    last_run: IngestionRunResponse | None = None
    next_run_at: datetime | None = None
    is_running: bool


class TriggerResponse(BaseModel):
    run_id: int
    message: str

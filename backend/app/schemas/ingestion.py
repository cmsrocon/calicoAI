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
    llm_calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    estimated_cost_usd: float | None = None


class IngestionStatusResponse(BaseModel):
    last_run: IngestionRunResponse | None = None
    next_run_at: datetime | None = None
    is_running: bool
    current_stage: str | None = None
    current_stage_detail: str | None = None
    last_error: str | None = None
    # Live stats for the active run (None when not running)
    live_calls: int | None = None
    live_tokens_in: int | None = None
    live_tokens_out: int | None = None
    live_cost_usd: float | None = None


class TriggerResponse(BaseModel):
    run_id: int
    message: str

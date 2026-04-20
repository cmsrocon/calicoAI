from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Trend(Base):
    __tablename__ = "trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trend_type: Mapped[str] = mapped_column(Text, nullable=False)  # vendor | vertical | overall
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # vendor_id or vertical_id
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_themes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array
    item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

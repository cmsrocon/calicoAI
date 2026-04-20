from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    feed_type: Mapped[str] = mapped_column(Text, nullable=False, default="rss")  # rss | html
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    trust_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    css_selector: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

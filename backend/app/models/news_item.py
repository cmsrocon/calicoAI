from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    external_url: Mapped[str] = mapped_column(Text, nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    language: Mapped[str] = mapped_column(Text, nullable=False, default="en")
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ai_relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    pros: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array
    cons: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON array
    balanced_take: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingestion_run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ingestion_runs.id", ondelete="SET NULL"), nullable=True)


class NewsItemVendor(Base):
    __tablename__ = "news_item_vendors"

    news_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_items.id", ondelete="CASCADE"), primary_key=True)
    vendor_id: Mapped[int] = mapped_column(Integer, ForeignKey("vendors.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class NewsItemVertical(Base):
    __tablename__ = "news_item_verticals"

    news_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("news_items.id", ondelete="CASCADE"), primary_key=True)
    vertical_id: Mapped[int] = mapped_column(Integer, ForeignKey("verticals.id", ondelete="CASCADE"), primary_key=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

import difflib
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news_item import NewsItem
from app.services.scraper_service import RawItem
from app.utils.text_utils import content_hash


async def hash_dedup(db: AsyncSession, items: list[RawItem]) -> tuple[list[RawItem], int]:
    """Remove items whose content_hash already exists in DB. Returns (new_items, duplicate_count)."""
    if not items:
        return [], 0
    hashes = [content_hash(item.title, item.url) for item in items]
    result = await db.execute(select(NewsItem.content_hash).where(NewsItem.content_hash.in_(hashes)))
    existing = {row[0] for row in result.all()}
    new_items = [item for item, h in zip(items, hashes) if h not in existing]
    duplicates = len(items) - len(new_items)
    return new_items, duplicates


def semantic_dedup_candidates(items: list[RawItem]) -> list[tuple[RawItem, RawItem]]:
    """Find pairs of items with title similarity > 0.7 as duplicate candidates."""
    candidates = []
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            ratio = difflib.SequenceMatcher(None, a.title.lower(), b.title.lower()).ratio()
            if ratio > 0.7:
                candidates.append((a, b))
    return candidates

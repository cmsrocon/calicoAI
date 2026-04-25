import difflib
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news_item import NewsItem
from app.services.scraper_service import RawItem
from app.utils.text_utils import content_hash


@dataclass
class StoryCluster:
    primary: RawItem
    related_items: list[RawItem]

    @property
    def all_items(self) -> list[RawItem]:
        return [self.primary, *self.related_items]


async def hash_dedup(db: AsyncSession, items: list[RawItem], topic_id: int) -> tuple[list[RawItem], int]:
    """Remove items whose content_hash already exists in DB. Returns (new_items, duplicate_count)."""
    if not items:
        return [], 0
    hashes = [content_hash(item.title, item.url) for item in items]
    result = await db.execute(
        select(NewsItem.content_hash).where(
            NewsItem.topic_id == topic_id,
            NewsItem.content_hash.in_(hashes),
        )
    )
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


def cluster_story_items(items: list[RawItem], duplicate_results: list[dict]) -> list[StoryCluster]:
    if not items:
        return []

    indexed_items = list(enumerate(items))
    item_by_url = {item.url: item for _, item in indexed_items}
    item_index_by_url = {item.url: index for index, item in indexed_items}
    parent = {item.url: item.url for _, item in indexed_items}
    keep_votes: dict[str, int] = defaultdict(int)

    def find(url: str) -> str:
        while parent[url] != url:
            parent[url] = parent[parent[url]]
            url = parent[url]
        return url

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for result in duplicate_results:
        keep_url = str(result.get("keep_url") or "").strip()
        discard_url = str(result.get("discard_url") or "").strip()
        if keep_url not in parent or discard_url not in parent:
            continue
        union(keep_url, discard_url)
        keep_votes[keep_url] += 1

    groups: dict[str, list[RawItem]] = defaultdict(list)
    for _, item in indexed_items:
        groups[find(item.url)].append(item)

    def primary_sort_key(item: RawItem) -> tuple[int, int, int, int]:
        published_rank = 1 if item.published_at is not None else 0
        return (
            keep_votes.get(item.url, 0),
            len(item.body_text or ""),
            published_rank,
            -item_index_by_url[item.url],
        )

    clusters_with_order: list[tuple[int, StoryCluster]] = []
    for grouped_items in groups.values():
        primary = max(grouped_items, key=primary_sort_key)
        related_items = [item for item in grouped_items if item.url != primary.url]
        min_index = min(item_index_by_url[item.url] for item in grouped_items)
        clusters_with_order.append((min_index, StoryCluster(primary=primary, related_items=related_items)))

    clusters_with_order.sort(key=lambda entry: entry[0])
    return [cluster for _, cluster in clusters_with_order]

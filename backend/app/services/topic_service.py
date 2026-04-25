from pathlib import Path
import json

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.news_item import NewsItem
from app.models.source import Source
from app.models.topic import Topic
from app.schemas.topic import TopicResponse
from app.services.llm_service import LLMService
from app.utils.date_utils import utcnow

DEFAULT_TOPIC_NAME = "AI"
DEFAULT_TOPIC_DESCRIPTION = (
    "Artificial intelligence, machine learning, large language models, AI policy, "
    "AI research, AI applications, and the companies building or deploying them."
)
DEFAULT_TOPIC_SLUG = "ai"


def _normalize_description(description: str | None) -> str | None:
    if description is None:
        return None
    trimmed = description.strip()
    return trimmed or None


async def _unique_topic_slug(db: AsyncSession, name: str, topic_id: int | None = None) -> str:
    base_slug = slugify(name) or "topic"
    slug = base_slug
    counter = 2
    while True:
        query = select(Topic).where(Topic.slug == slug)
        if topic_id is not None:
            query = query.where(Topic.id != topic_id)
        existing = (await db.execute(query)).scalar_one_or_none()
        if not existing:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


async def get_topic(db: AsyncSession, topic_id: int) -> Topic | None:
    return (await db.execute(select(Topic).where(Topic.id == topic_id))).scalar_one_or_none()


async def get_default_topic(db: AsyncSession) -> Topic | None:
    return (await db.execute(
        select(Topic).where(Topic.is_default == True).order_by(Topic.id.asc())
    )).scalar_one_or_none()


async def ensure_default_topic(db: AsyncSession) -> Topic:
    existing = await get_default_topic(db)
    if existing:
        return existing

    fallback = (await db.execute(select(Topic).order_by(Topic.id.asc()))).scalars().first()
    if fallback:
        fallback.is_default = True
        fallback.updated_at = utcnow()
        await db.commit()
        await db.refresh(fallback)
        return fallback

    topic = Topic(
        name=DEFAULT_TOPIC_NAME,
        slug=DEFAULT_TOPIC_SLUG,
        description=DEFAULT_TOPIC_DESCRIPTION,
        is_default=True,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


async def list_topics_with_counts(db: AsyncSession) -> list[TopicResponse]:
    topics = (await db.execute(select(Topic).order_by(Topic.is_default.desc(), Topic.name.asc()))).scalars().all()
    source_counts = dict((await db.execute(
        select(Source.topic_id, func.count(Source.id)).group_by(Source.topic_id)
    )).all())
    article_counts = dict((await db.execute(
        select(NewsItem.topic_id, func.count(NewsItem.id)).group_by(NewsItem.topic_id)
    )).all())
    return [
        TopicResponse(
            id=t.id,
            name=t.name,
            slug=t.slug,
            description=t.description,
            is_default=t.is_default,
            source_count=int(source_counts.get(t.id, 0)),
            article_count=int(article_counts.get(t.id, 0)),
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in topics
    ]


def _sanitize_seeded_source(topic_id: int, payload: dict) -> dict | None:
    url = str(payload.get("url", "")).strip()
    name = str(payload.get("name", "")).strip()
    if not url or not name:
        return None
    feed_type = str(payload.get("feed_type", "rss")).strip().lower()
    if feed_type not in {"rss", "html"}:
        feed_type = "rss"
    trust_weight = payload.get("trust_weight", 1.4)
    try:
        trust_weight = max(0.5, min(2.0, float(trust_weight)))
    except (TypeError, ValueError):
        trust_weight = 1.4
    css_selector = payload.get("css_selector")
    if css_selector is not None:
        css_selector = str(css_selector).strip() or None
    return {
        "topic_id": topic_id,
        "name": name,
        "url": url,
        "feed_type": feed_type,
        "trust_weight": trust_weight,
        "css_selector": css_selector,
        "is_active": bool(payload.get("is_active", True)),
    }


async def seed_default_topic_sources(db: AsyncSession, topic_id: int) -> int:
    seeds_path = Path(__file__).parent.parent.parent / "seeds" / "default_sources.json"
    if not seeds_path.exists():
        return 0

    sources_data = json.loads(seeds_path.read_text())
    inserted = 0
    for raw_source in sources_data:
        payload = _sanitize_seeded_source(topic_id, raw_source)
        if not payload:
            continue
        existing = (await db.execute(
            select(Source).where(Source.topic_id == topic_id, Source.url == payload["url"])
        )).scalar_one_or_none()
        if existing:
            continue
        db.add(Source(**payload))
        inserted += 1
    await db.commit()
    return inserted


async def seed_sources_for_topic(
    db: AsyncSession,
    llm: LLMService,
    topic: Topic,
) -> tuple[int, str, str | None]:
    try:
        suggestions = await llm.suggest_topic_sources(topic.name, topic.description or "")
    except Exception as exc:
        return 0, "warning", str(exc)

    inserted = 0
    for raw_source in suggestions[:10]:
        payload = _sanitize_seeded_source(topic.id, raw_source)
        if not payload:
            continue
        existing = (await db.execute(
            select(Source).where(Source.topic_id == topic.id, Source.url == payload["url"])
        )).scalar_one_or_none()
        if existing:
            continue
        db.add(Source(**payload))
        inserted += 1

    await db.commit()
    if inserted == 0:
        return 0, "warning", "The model returned no usable source suggestions."
    return inserted, "ok", None


async def create_topic(db: AsyncSession, name: str, description: str | None = None) -> Topic:
    normalized_name = name.strip()
    normalized_description = _normalize_description(description)
    topic = Topic(
        name=normalized_name,
        slug=await _unique_topic_slug(db, normalized_name),
        description=normalized_description,
        is_default=False,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


async def update_topic(topic: Topic, db: AsyncSession, name: str | None = None, description: str | None = None) -> Topic:
    if name is not None:
        topic.name = name.strip()
        topic.slug = await _unique_topic_slug(db, topic.name, topic.id)
    if description is not None:
        topic.description = _normalize_description(description)
    topic.updated_at = utcnow()
    await db.commit()
    await db.refresh(topic)
    return topic

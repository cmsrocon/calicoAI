from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.topic import Topic
from app.schemas.topic import TopicCreate, TopicCreateResponse, TopicResponse, TopicUpdate
from app.services.auth_service import UserUsageTracker, require_admin_user
from app.services.llm_service import get_llm_service
from app.services.topic_service import create_topic, get_topic, list_topics_with_counts, seed_sources_for_topic, update_topic

router = APIRouter(prefix="/topics", tags=["topics"])


@router.get("", response_model=list[TopicResponse])
async def list_topics(db: AsyncSession = Depends(get_db)):
    return await list_topics_with_counts(db)


@router.post("", response_model=TopicCreateResponse, status_code=201)
async def create_topic_endpoint(body: TopicCreate, db: AsyncSession = Depends(get_db), user=Depends(require_admin_user)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Topic name is required")
    existing = (await db.execute(select(Topic).where(Topic.name.ilike(body.name.strip())))).scalar_one_or_none()
    if existing:
        topics = await list_topics_with_counts(db)
        topic_response = next(t for t in topics if t.id == existing.id)
        return TopicCreateResponse(
            topic=topic_response,
            seeded_sources_count=0,
            seed_status="ok",
            seed_message="Existing shared topic reused; no duplicate topic or source-seeding call was created.",
        )
    topic = await create_topic(db, body.name, body.description)
    llm = get_llm_service().fork(UserUsageTracker(user.id, "topics.seed_sources"))
    seeded_sources_count, seed_status, seed_message = await seed_sources_for_topic(db, llm, topic)
    topics = await list_topics_with_counts(db)
    topic_response = next(t for t in topics if t.id == topic.id)
    return TopicCreateResponse(
        topic=topic_response,
        seeded_sources_count=seeded_sources_count,
        seed_status=seed_status,
        seed_message=seed_message,
    )


@router.patch("/{topic_id}", response_model=TopicResponse)
async def update_topic_endpoint(topic_id: int, body: TopicUpdate, db: AsyncSession = Depends(get_db), user=Depends(require_admin_user)):
    topic = await get_topic(db, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    if body.name is not None:
        if not body.name.strip():
            raise HTTPException(status_code=400, detail="Topic name is required")
        existing = (await db.execute(
            select(Topic).where(Topic.name.ilike(body.name.strip()), Topic.id != topic_id)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="Topic name already exists")
    updated = await update_topic(topic, db, body.name, body.description)
    topics = await list_topics_with_counts(db)
    return next(t for t in topics if t.id == updated.id)


@router.delete("/{topic_id}", status_code=204)
async def delete_topic_endpoint(topic_id: int, db: AsyncSession = Depends(get_db), user=Depends(require_admin_user)):
    topic = await get_topic(db, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic.is_default:
        raise HTTPException(status_code=400, detail="The default topic cannot be deleted")
    topic_count = len((await db.execute(select(Topic.id))).scalars().all())
    if topic_count <= 1:
        raise HTTPException(status_code=400, detail="At least one topic must remain")
    await db.delete(topic)
    await db.commit()

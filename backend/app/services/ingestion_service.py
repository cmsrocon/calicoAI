import asyncio
import json
import logging
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ingestion_run import IngestionRun
from app.models.news_item import NewsItem, NewsItemVendor, NewsItemVertical
from app.models.source import Source
from app.models.topic import Topic
from app.models.vendor import Vendor
from app.models.vertical import Vertical
from app.services import dedup_service, scraper_service
from app.services.llm_service import LLMService
from app.services.topic_service import ensure_default_topic
from app.services.trend_service import update_trends
from app.services.vendor_service import get_or_create_vendor
from app.services.vertical_service import get_or_create_vertical
from app.utils.date_utils import utcnow
from app.utils.text_utils import content_hash, truncate

logger = logging.getLogger(__name__)

_is_running = False
_current_stage: str = ""
_current_stage_detail: str = ""
_last_error: str | None = None
_current_topic_id: int | None = None


def is_running() -> bool:
    return _is_running


_llm_ref: "LLMService | None" = None


def get_progress() -> dict:
    base = {"stage": _current_stage, "detail": _current_stage_detail, "last_error": _last_error}
    if _llm_ref is not None:
        base.update(_llm_ref.get_session_stats())
    return base


def should_reuse_active_run(topic_id: int | None) -> bool:
    if not _is_running:
        return False
    if _current_topic_id is None:
        return True
    return _current_topic_id == topic_id


async def get_recent_matching_run(db: AsyncSession, topic_id: int | None) -> IngestionRun | None:
    window_start = utcnow() - timedelta(minutes=settings.refresh_cooldown_minutes)
    query = select(IngestionRun).where(
        IngestionRun.status == "success",
        IngestionRun.finished_at.is_not(None),
        IngestionRun.finished_at >= window_start,
    )
    if topic_id is None:
        query = query.where(IngestionRun.topic_id.is_(None))
    else:
        query = query.where(or_(IngestionRun.topic_id == topic_id, IngestionRun.topic_id.is_(None)))
    query = query.order_by(IngestionRun.finished_at.desc())
    return (await db.execute(query)).scalars().first()


def _is_db_locked(exc: Exception) -> bool:
    return "database is locked" in str(exc).lower()


def _serialize_story_sources(items: list[scraper_service.RawItem], primary_url: str) -> list[dict]:
    seen_urls: set[str] = set()
    documents = []
    for item in items:
        if item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        documents.append({
            "url": item.url,
            "source_name": item.source_name,
            "headline": item.title,
            "published_at": item.published_at.isoformat() if item.published_at else None,
            "is_primary": item.url == primary_url,
        })
    documents.sort(key=lambda document: (not document["is_primary"], document["source_name"] or "", document["headline"]))
    return documents


def _build_story_body(items: list[scraper_service.RawItem]) -> str:
    sections = []
    for index, item in enumerate(items[:6], start=1):
        published = item.published_at.isoformat() if item.published_at else "unknown"
        sections.append(
            f"Source document {index}\n"
            f"Source: {item.source_name}\n"
            f"Headline: {item.title}\n"
            f"URL: {item.url}\n"
            f"Published: {published}\n"
            f"Excerpt: {truncate(item.body_text or '', 2200)}"
        )
    return truncate("\n\n---\n\n".join(sections), 14000)


def _build_relevance_snippet(cluster: dedup_service.StoryCluster) -> str:
    sections = []
    for item in cluster.all_items[:3]:
        sections.append(
            f"{item.source_name}: {item.title}\n"
            f"{truncate(item.body_text or '', 700)}"
        )
    return truncate("\n\n".join(sections), 2200)


def _load_source_documents(raw: str | None, fallback: dict | None = None) -> list[dict]:
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [entry for entry in parsed if isinstance(entry, dict)]
        except json.JSONDecodeError:
            logger.warning("Failed to decode source_documents JSON during reprocessing")
    return [fallback] if fallback else []


async def _create_run_with_retry(
    db: AsyncSession,
    triggered_by: str,
    topic_id: int | None,
    user_id: int | None,
    attempts: int = 5,
) -> IngestionRun:
    for attempt in range(attempts):
        run = IngestionRun(
            triggered_by=triggered_by,
            status="running",
            started_at=utcnow(),
            topic_id=topic_id,
            user_id=user_id,
        )
        db.add(run)
        try:
            await db.commit()
            await db.refresh(run)
            return run
        except OperationalError as exc:
            await db.rollback()
            if not _is_db_locked(exc) or attempt == attempts - 1:
                raise
            wait = 0.5 * (attempt + 1)
            logger.warning("Database locked while creating ingestion run; retrying in %.1fs", wait)
            await asyncio.sleep(wait)
    raise RuntimeError("Failed to create ingestion run")


async def run_ingestion(
    db: AsyncSession,
    llm: LLMService,
    triggered_by: str = "manual",
    topic_id: int | None = None,
    user_id: int | None = None,
) -> int:
    global _is_running, _current_stage, _current_stage_detail, _llm_ref, _last_error, _current_topic_id
    if _is_running:
        raise RuntimeError("Ingestion is already running")
    _is_running = True
    _current_topic_id = topic_id
    _llm_ref = llm
    _last_error = None
    run_id: int | None = None

    try:
        run = await _create_run_with_retry(db, triggered_by, topic_id, user_id)
        run_id = run.id
        llm.reset_session()
        await _execute_pipeline(db, llm, run_id, topic_id=topic_id)
    except Exception as exc:
        logger.exception("Ingestion pipeline failed")
        if run_id is not None:
            result = await db.execute(select(IngestionRun).where(IngestionRun.id == run_id))
            run = result.scalar_one()
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = utcnow()
            await db.commit()
        else:
            _last_error = str(exc)
            raise
    finally:
        _current_stage = ""
        _current_stage_detail = ""
        _is_running = False
        _current_topic_id = None
        _llm_ref = None

    if run_id is None:
        raise RuntimeError("Failed to create ingestion run")
    _last_error = None
    return run_id


async def _execute_pipeline(db: AsyncSession, llm: LLMService, run_id: int, topic_id: int | None = None) -> None:
    global _current_stage, _current_stage_detail

    await ensure_default_topic(db)
    topics_query = select(Topic).order_by(Topic.is_default.desc(), Topic.name.asc())
    if topic_id is not None:
        topics_query = topics_query.where(Topic.id == topic_id)
    topics = (await db.execute(topics_query)).scalars().all()
    if not topics:
        raise RuntimeError("Topic not found")
    topic_by_id = {topic.id: topic for topic in topics}

    _current_stage = "Fetching articles"
    sources_query = select(Source).where(Source.is_active == True)
    if topic_id is not None:
        sources_query = sources_query.where(Source.topic_id == topic_id)
    sources = (await db.execute(
        sources_query.order_by(Source.topic_id.asc(), Source.name.asc())
    )).scalars().all()
    if topic_id is not None:
        _current_stage_detail = f"Loading from {len(sources)} active sources in {topics[0].name}..."
    else:
        _current_stage_detail = f"Loading from {len(sources)} active sources across {len(topics)} topics..."
    raw_items_by_topic: dict[int, list] = {topic.id: [] for topic in topics}
    items_fetched = 0

    async def fetch_one(source: Source):
        items, error = await scraper_service.fetch_source(
            source.id, source.name, source.url, source.feed_type, source.css_selector
        )
        source.last_fetched_at = utcnow()
        source.last_error = error
        return source, items

    results = await asyncio.gather(*[fetch_one(source) for source in sources], return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            continue
        source, items = res
        raw_items_by_topic.setdefault(source.topic_id, []).extend(items)
        items_fetched += len(items)

    await db.commit()
    logger.info("Stage 1: Fetched %s items from %s sources", items_fetched, len(sources))

    known_vendors = [vendor.name for vendor in (await db.execute(select(Vendor))).scalars().all()]
    known_verticals = [vertical.name for vertical in (await db.execute(select(Vertical))).scalars().all()]

    items_new = 0
    duplicates_total = 0

    for topic in topics:
        raw_items = raw_items_by_topic.get(topic.id, [])
        if not raw_items:
            continue

        _current_stage = "Deduplicating"
        _current_stage_detail = f"{topic.name}: checking {len(raw_items)} fetched articles against existing items..."
        new_items, duplicates = await dedup_service.hash_dedup(db, raw_items, topic.id)
        duplicates_total += duplicates
        logger.info("Topic %s stage 2: %s new, %s duplicates", topic.name, len(new_items), duplicates)
        if not new_items:
            continue

        _current_stage = "Semantic deduplication"
        candidates = dedup_service.semantic_dedup_candidates(new_items)
        _current_stage_detail = f"{topic.name}: checking {len(candidates)} similar article pairs..."
        duplicate_results: list[dict] = []
        if candidates:
            pairs = [(a.title, a.url, b.title, b.url) for a, b in candidates[:20]]
            try:
                duplicate_results = await llm.check_duplicates(pairs)
            except Exception:
                pass
        story_clusters = dedup_service.cluster_story_items(new_items, duplicate_results)
        semantic_duplicates = sum(len(cluster.related_items) for cluster in story_clusters)
        duplicates_total += semantic_duplicates
        logger.info("Topic %s stage 3: %s story clusters after semantic dedup", topic.name, len(story_clusters))
        if not story_clusters:
            continue

        _current_stage = "Filtering for relevance"
        _current_stage_detail = f"{topic.name}: scoring {len(story_clusters)} story clusters for topic relevance..."
        rel_counter = {"done": 0}

        async def check_rel(cluster: dedup_service.StoryCluster):
            try:
                primary = cluster.primary
                res = await llm.check_topic_relevance(
                    primary.title,
                    _build_relevance_snippet(cluster),
                    topic.name,
                    topic.description or "",
                )
                score = float(res.get("topic_relevance_score", res.get("ai_relevance_score", 0)))
                return cluster, score
            except Exception as exc:
                logger.debug("Relevance check failed for '%s': %s", cluster.primary.title[:60], exc)
                return cluster, 0.5

        sem = asyncio.Semaphore(10)

        async def check_with_sem(cluster: dedup_service.StoryCluster):
            async with sem:
                result = await check_rel(cluster)
                rel_counter["done"] += 1
                _current_stage_detail = f"{topic.name}: relevance check {rel_counter['done']}/{len(story_clusters)}"
                return result

        rel_results = await asyncio.gather(*[check_with_sem(cluster) for cluster in story_clusters])
        relevant_clusters = [(cluster, score) for cluster, score in rel_results if score >= 0.4]
        logger.info("Topic %s stage 4: %s relevant story clusters", topic.name, len(relevant_clusters))
        if not relevant_clusters:
            continue

        _current_stage = "AI analysis"
        _current_stage_detail = f"{topic.name}: analysing {len(relevant_clusters)} distilled stories..."
        proc_sem = asyncio.Semaphore(5)
        proc_counter = {"done": 0}

        async def process_one(cluster: dedup_service.StoryCluster, relevance_score: float):
            async with proc_sem:
                primary = cluster.primary
                story_items = cluster.all_items
                source_documents = _serialize_story_sources(story_items, primary.url)
                story_body = _build_story_body(story_items)
                try:
                    processed = await llm.process_item(
                        title=primary.title,
                        url=primary.url,
                        source_name=primary.source_name,
                        body=story_body,
                        topic_name=topic.name,
                        topic_description=topic.description or "",
                        known_vendors=known_vendors,
                        known_verticals=known_verticals,
                        source_documents=source_documents,
                    )
                    proc_counter["done"] += 1
                    _current_stage_detail = f"{topic.name}: AI analysis {proc_counter['done']}/{len(relevant_clusters)}"
                    return cluster, relevance_score, source_documents, story_body, processed, None
                except Exception as exc:
                    proc_counter["done"] += 1
                    return cluster, relevance_score, source_documents, story_body, None, str(exc)

        proc_results = await asyncio.gather(*[process_one(cluster, score) for cluster, score in relevant_clusters])

        for index, (cluster, rel_score, source_documents, story_body, processed, error) in enumerate(proc_results, start=1):
            primary = cluster.primary
            _current_stage_detail = f"{topic.name}: storing story {index}/{len(relevant_clusters)}"
            if error:
                logger.warning("Topic %s stage 5: LLM failed for '%s': %s", topic.name, primary.title[:60], error)

            news_item = NewsItem(
                topic_id=topic.id,
                content_hash=content_hash(primary.title, primary.url),
                external_url=primary.url,
                headline=processed.headline if processed else primary.title,
                source_id=primary.source_id if primary.source_id != 0 else None,
                published_at=primary.published_at,
                ingested_at=utcnow(),
                language=processed.language if processed else "en",
                raw_content=story_body,
                source_documents=json.dumps(source_documents),
                summary=processed.summary if processed else None,
                why_it_matters=processed.why_it_matters if processed else None,
                importance_rank=processed.importance_rank if processed else None,
                ai_relevance_score=rel_score,
                pros=json.dumps(processed.pros if processed else []),
                cons=json.dumps(processed.cons if processed else []),
                balanced_take=processed.balanced_take if processed else None,
                is_processed=processed is not None,
                processing_error=error,
                ingestion_run_id=run_id,
            )
            db.add(news_item)
            await db.flush()

            if processed:
                await _apply_tags(db, llm, news_item, processed, known_vendors, known_verticals)

            items_new += 1

        await db.commit()
        logger.info("Topic %s stage 5: stored %s new items", topic.name, len(proc_results))

    incomplete_query = select(NewsItem).where(NewsItem.is_processed == False)
    if topic_id is not None:
        incomplete_query = incomplete_query.where(NewsItem.topic_id == topic_id)
    incomplete = (await db.execute(incomplete_query.limit(50))).scalars().all()

    if incomplete:
        _current_stage = "Completing incomplete articles"
        logger.info("Stage 5b: Reprocessing %s incomplete articles", len(incomplete))
        for idx, news_item in enumerate(incomplete, start=1):
            topic = topic_by_id.get(news_item.topic_id) or await ensure_default_topic(db)
            _current_stage_detail = f"{topic.name}: completing {idx}/{len(incomplete)}"
            source_name: str | None = None
            if news_item.source_id:
                source = (await db.execute(select(Source).where(Source.id == news_item.source_id))).scalar_one_or_none()
                source_name = source.name if source else None
            source_documents = _load_source_documents(
                news_item.source_documents,
                fallback={
                    "url": news_item.external_url,
                    "source_name": source_name,
                    "headline": news_item.headline,
                    "published_at": news_item.published_at.isoformat() if news_item.published_at else None,
                    "is_primary": True,
                },
            )
            try:
                processed = await llm.process_item(
                    title=news_item.headline,
                    url=news_item.external_url,
                    source_name=source_name or "",
                    body=news_item.raw_content or "",
                    topic_name=topic.name,
                    topic_description=topic.description or "",
                    known_vendors=known_vendors,
                    known_verticals=known_verticals,
                    source_documents=source_documents,
                )
                news_item.summary = processed.summary
                news_item.why_it_matters = processed.why_it_matters
                news_item.importance_rank = processed.importance_rank
                news_item.language = processed.language
                news_item.pros = json.dumps(processed.pros)
                news_item.cons = json.dumps(processed.cons)
                news_item.balanced_take = processed.balanced_take
                news_item.is_processed = True
                news_item.processing_error = None
                await db.flush()
                await _apply_tags(db, llm, news_item, processed, known_vendors, known_verticals)
                logger.info("Stage 5b: completed item %s", news_item.id)
            except Exception as exc:
                logger.warning("Stage 5b: failed to complete item %s: %s", news_item.id, exc)
                news_item.processing_error = str(exc)

        await db.commit()

    _current_stage = "Analysing trends"
    _current_stage_detail = "Building topic, entity, and theme trend summaries..."
    try:
        await update_trends(db, llm)
        logger.info("Stage 6: Trends updated")
    except Exception as exc:
        logger.warning("Trend update failed: %s", exc)

    _current_stage = "Finalising"
    _current_stage_detail = "Writing run summary..."
    stats = llm.get_session_stats()
    run = (await db.execute(select(IngestionRun).where(IngestionRun.id == run_id))).scalar_one()
    run.status = "success"
    run.finished_at = utcnow()
    run.items_fetched = items_fetched
    run.items_new = items_new
    run.items_duplicate = duplicates_total
    run.llm_calls = stats["calls"]
    run.tokens_in = stats["tokens_in"]
    run.tokens_out = stats["tokens_out"]
    run.estimated_cost_usd = stats["estimated_cost_usd"]
    await db.commit()
    logger.info(
        "Ingestion run %s complete: %s new items, %s LLM calls, %s+%s tokens, ~$%.4f",
        run_id,
        items_new,
        stats["calls"],
        stats["tokens_in"],
        stats["tokens_out"],
        stats["estimated_cost_usd"],
    )


async def _apply_tags(
    db: AsyncSession,
    llm: LLMService,
    news_item: NewsItem,
    processed,
    known_vendors: list[str],
    known_verticals: list[str],
) -> None:
    for new_vname in processed.new_vendors:
        if new_vname not in known_vendors:
            try:
                raw_ctx = (news_item.raw_content or "")[:300]
                vdata = await llm.describe_vendor(new_vname, raw_ctx)
                await get_or_create_vendor(
                    db,
                    vdata.get("name", new_vname),
                    vdata.get("description", ""),
                    vdata.get("aliases", []),
                )
                known_vendors.append(vdata.get("name", new_vname))
            except Exception:
                await get_or_create_vendor(db, new_vname)
                known_vendors.append(new_vname)

    existing_vendor_ids = {
        row[0] for row in (await db.execute(
            select(NewsItemVendor.vendor_id).where(NewsItemVendor.news_item_id == news_item.id)
        )).all()
    }
    for vtag in processed.vendor_tags:
        vendor = await get_or_create_vendor(db, vtag["name"])
        if vendor.id not in existing_vendor_ids:
            db.add(NewsItemVendor(news_item_id=news_item.id, vendor_id=vendor.id, confidence=vtag.get("confidence", 1.0)))
            existing_vendor_ids.add(vendor.id)

    existing_vertical_ids = {
        row[0] for row in (await db.execute(
            select(NewsItemVertical.vertical_id).where(NewsItemVertical.news_item_id == news_item.id)
        )).all()
    }
    for vttag in processed.vertical_tags:
        vertical = await get_or_create_vertical(db, vttag["name"])
        if vertical and vertical.id not in existing_vertical_ids:
            db.add(NewsItemVertical(news_item_id=news_item.id, vertical_id=vertical.id, confidence=vttag.get("confidence", 1.0)))
            existing_vertical_ids.add(vertical.id)
            if vertical.name not in known_verticals:
                known_verticals.append(vertical.name)

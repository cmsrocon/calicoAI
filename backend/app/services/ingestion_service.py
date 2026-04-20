import asyncio
import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingestion_run import IngestionRun
from app.models.news_item import NewsItem, NewsItemVendor, NewsItemVertical
from app.models.source import Source
from app.models.vendor import Vendor
from app.models.vertical import Vertical
from app.services import dedup_service, scraper_service
from app.services.llm_service import LLMService
from app.services.trend_service import update_trends
from app.services.vendor_service import get_or_create_vendor
from app.services.vertical_service import get_or_create_vertical
from app.utils.date_utils import utcnow
from app.utils.text_utils import content_hash

logger = logging.getLogger(__name__)

_is_running = False
_current_stage: str = ""
_current_stage_detail: str = ""


def is_running() -> bool:
    return _is_running


_llm_ref: "LLMService | None" = None


def get_progress() -> dict:
    base = {"stage": _current_stage, "detail": _current_stage_detail}
    if _llm_ref is not None:
        base.update(_llm_ref.get_session_stats())
    return base


async def run_ingestion(db: AsyncSession, llm: LLMService, triggered_by: str = "manual") -> int:
    global _is_running, _current_stage, _current_stage_detail, _llm_ref
    if _is_running:
        raise RuntimeError("Ingestion is already running")
    _is_running = True
    _llm_ref = llm

    run = IngestionRun(triggered_by=triggered_by, status="running", started_at=utcnow())
    db.add(run)
    await db.commit()
    await db.refresh(run)
    run_id = run.id

    llm.reset_session()
    try:
        await _execute_pipeline(db, llm, run_id)
    except Exception as e:
        logger.exception("Ingestion pipeline failed")
        result = await db.execute(select(IngestionRun).where(IngestionRun.id == run_id))
        r = result.scalar_one()
        r.status = "failed"
        r.error_message = str(e)
        r.finished_at = utcnow()
        await db.commit()
    finally:
        _current_stage = ""
        _current_stage_detail = ""
        _is_running = False
        _llm_ref = None

    return run_id


async def _execute_pipeline(db: AsyncSession, llm: LLMService, run_id: int) -> None:
    global _current_stage, _current_stage_detail

    # Stage 1: Fetch
    _current_stage = "Fetching articles"
    sources = (await db.execute(select(Source).where(Source.is_active == True))).scalars().all()
    _current_stage_detail = f"Loading from {len(sources)} active sources…"
    raw_items = []
    items_fetched = 0

    async def fetch_one(source: Source):
        items, error = await scraper_service.fetch_source(
            source.id, source.name, source.url, source.feed_type, source.css_selector
        )
        source.last_fetched_at = utcnow()
        source.last_error = error
        return items

    fetch_tasks = [fetch_one(s) for s in sources]
    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, list):
            raw_items.extend(res)
            items_fetched += len(res)

    await db.commit()
    logger.info(f"Stage 1: Fetched {items_fetched} items from {len(sources)} sources")

    # Stage 2: Hash dedup
    _current_stage = "Deduplicating"
    _current_stage_detail = f"Checking {items_fetched} articles against database…"
    new_items, duplicates = await dedup_service.hash_dedup(db, raw_items)
    logger.info(f"Stage 2: {len(new_items)} new, {duplicates} duplicates")

    # Stage 3: Semantic dedup
    _current_stage = "Semantic deduplication"
    candidates = dedup_service.semantic_dedup_candidates(new_items)
    _current_stage_detail = f"Checking {len(candidates)} similar article pairs…"
    discard_urls: set[str] = set()
    if candidates:
        pairs = [(a.title, a.url, b.title, b.url) for a, b in candidates[:20]]
        try:
            dup_results = await llm.check_duplicates(pairs)
            discard_urls = {d["discard_url"] for d in dup_results}
        except Exception:
            pass
    new_items = [i for i in new_items if i.url not in discard_urls]
    logger.info(f"Stage 3: {len(new_items)} after semantic dedup")

    # Stage 4: Relevance filter
    _current_stage = "Filtering for relevance"
    _current_stage_detail = f"Scoring {len(new_items)} articles for AI relevance…"
    rel_counter = {"done": 0}

    async def check_rel(item):
        try:
            res = await llm.check_relevance(item.title, item.body_text)
            return item, float(res.get("ai_relevance_score", 0))
        except Exception as e:
            logger.debug(f"Relevance check failed for '{item.title[:60]}': {e}")
            return item, 0.5

    sem = asyncio.Semaphore(10)
    async def check_with_sem(item):
        async with sem:
            result = await check_rel(item)
            rel_counter["done"] += 1
            _current_stage_detail = f"Relevance check {rel_counter['done']}/{len(new_items)}"
            return result

    rel_results = await asyncio.gather(*[check_with_sem(i) for i in new_items])
    relevant_items = [(item, score) for item, score in rel_results if score >= 0.4]
    logger.info(f"Stage 4: {len(relevant_items)} relevant items")

    # Load known vendors + verticals for LLM context
    known_vendors = [v.name for v in (await db.execute(select(Vendor))).scalars().all()]
    known_verticals = [v.name for v in (await db.execute(select(Vertical))).scalars().all()]

    # Stage 5: Full processing of new items
    _current_stage = "AI analysis"
    _current_stage_detail = f"Analysing {len(relevant_items)} new articles…"
    proc_sem = asyncio.Semaphore(5)
    proc_counter = {"done": 0}

    async def process_one(item, relevance_score):
        async with proc_sem:
            try:
                processed = await llm.process_item(
                    item.title, item.url, item.source_name, item.body_text,
                    known_vendors, known_verticals
                )
                proc_counter["done"] += 1
                _current_stage_detail = f"AI analysis {proc_counter['done']}/{len(relevant_items)}: {item.title[:50]}…"
                return item, relevance_score, processed, None
            except Exception as e:
                proc_counter["done"] += 1
                return item, relevance_score, None, str(e)

    proc_results = await asyncio.gather(*[process_one(item, score) for item, score in relevant_items])

    items_new = 0
    proc_count = 0
    for item, rel_score, processed, error in proc_results:
        proc_count += 1
        _current_stage_detail = f"Storing article {proc_count}/{len(relevant_items)}…"
        if error:
            logger.warning(f"Stage 5: LLM failed for '{item.title[:60]}': {error}")
        h = content_hash(item.title, item.url)
        news_item = NewsItem(
            content_hash=h,
            external_url=item.url,
            headline=processed.headline if processed else item.title,
            source_id=item.source_id if item.source_id != 0 else None,
            published_at=item.published_at,
            ingested_at=utcnow(),
            language=processed.language if processed else "en",
            raw_content=item.body_text,
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
    logger.info(f"Stage 5: Stored {items_new} new items")

    # Stage 5b: Reprocess incomplete items from previous runs
    incomplete = (await db.execute(
        select(NewsItem).where(NewsItem.is_processed == False).limit(50)
    )).scalars().all()

    if incomplete:
        _current_stage = "Completing incomplete articles"
        logger.info(f"Stage 5b: Reprocessing {len(incomplete)} incomplete articles")
        for idx, ni in enumerate(incomplete):
            _current_stage_detail = f"Completing {idx + 1}/{len(incomplete)}: {ni.headline[:60]}…"
            src_name: str | None = None
            if ni.source_id:
                src = (await db.execute(select(Source).where(Source.id == ni.source_id))).scalar_one_or_none()
                src_name = src.name if src else None
            try:
                processed = await llm.process_item(
                    ni.headline, ni.external_url, src_name or "",
                    ni.raw_content or "", known_vendors, known_verticals
                )
                ni.summary = processed.summary
                ni.why_it_matters = processed.why_it_matters
                ni.importance_rank = processed.importance_rank
                ni.language = processed.language
                ni.pros = json.dumps(processed.pros)
                ni.cons = json.dumps(processed.cons)
                ni.balanced_take = processed.balanced_take
                ni.is_processed = True
                ni.processing_error = None
                await db.flush()
                await _apply_tags(db, llm, ni, processed, known_vendors, known_verticals)
                logger.info(f"Stage 5b: Completed item {ni.id}")
            except Exception as e:
                logger.warning(f"Stage 5b: Failed to complete item {ni.id}: {e}")
                ni.processing_error = str(e)

        await db.commit()

    # Stage 6: Trend update
    _current_stage = "Analysing trends"
    _current_stage_detail = "Building vendor and sector trend summaries…"
    try:
        await update_trends(db, llm)
        logger.info("Stage 6: Trends updated")
    except Exception as e:
        logger.warning(f"Trend update failed: {e}")

    # Stage 7: Finalize
    _current_stage = "Finalising"
    _current_stage_detail = "Writing run summary…"
    stats = llm.get_session_stats()
    result = await db.execute(select(IngestionRun).where(IngestionRun.id == run_id))
    run = result.scalar_one()
    run.status = "success"
    run.finished_at = utcnow()
    run.items_fetched = items_fetched
    run.items_new = items_new
    run.items_duplicate = duplicates
    run.llm_calls = stats["calls"]
    run.tokens_in = stats["tokens_in"]
    run.tokens_out = stats["tokens_out"]
    run.estimated_cost_usd = stats["estimated_cost_usd"]
    await db.commit()
    logger.info(
        f"Ingestion run {run_id} complete: {items_new} new items, "
        f"{stats['calls']} LLM calls, {stats['tokens_in']}+{stats['tokens_out']} tokens, "
        f"~${stats['estimated_cost_usd']:.4f}"
    )


async def _apply_tags(
    db: AsyncSession, llm: LLMService, news_item: NewsItem,
    processed, known_vendors: list, known_verticals: list
) -> None:
    # Handle new vendors
    for new_vname in processed.new_vendors:
        if new_vname not in known_vendors:
            try:
                raw_ctx = (news_item.raw_content or "")[:300]
                vdata = await llm.describe_vendor(new_vname, raw_ctx)
                await get_or_create_vendor(db, vdata.get("name", new_vname),
                                           vdata.get("description", ""),
                                           vdata.get("aliases", []))
                known_vendors.append(vdata.get("name", new_vname))
            except Exception:
                await get_or_create_vendor(db, new_vname)
                known_vendors.append(new_vname)

    # Link vendors (skip if already linked)
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

    # Link verticals (skip if already linked)
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

import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_config
from app.database import get_db
from app.models.app_setting import AppSetting
from app.services.llm_service import LLMService, get_llm_service, set_llm_service
from app.utils.date_utils import utcnow

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_SETTINGS = {
    "llm_provider": "anthropic",
    "llm_model": "claude-sonnet-4-6",
    "llm_max_tokens": "1500",
    "schedule_hour": "6",
    "schedule_minute": "0",
}

# Keys that contain secrets — masked before returning to the frontend
_SECRET_KEYS = {"anthropic_api_key", "openai_api_key", "minimax_api_key"}


def _mask(value: str) -> str:
    """Return a masked version showing only the last 6 characters."""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return "*" * (len(value) - 6) + value[-6:]


def _is_masked(value: str) -> bool:
    return "*" in value


async def load_settings(db: AsyncSession) -> dict[str, str]:
    """Return settings with secret values masked."""
    rows = (await db.execute(select(AppSetting))).scalars().all()
    result = dict(DEFAULT_SETTINGS)
    result.update({r.key: r.value for r in rows})
    for k in _SECRET_KEYS:
        if k in result:
            result[k] = _mask(result[k])
    return result


async def load_raw_settings(db: AsyncSession) -> dict[str, str]:
    """Return settings with real (unmasked) secret values for internal use."""
    rows = (await db.execute(select(AppSetting))).scalars().all()
    result = dict(DEFAULT_SETTINGS)
    result.update({r.key: r.value for r in rows})
    # Fall back to env vars if not stored in DB
    if not result.get("anthropic_api_key"):
        result["anthropic_api_key"] = app_config.anthropic_api_key
    if not result.get("openai_api_key"):
        result["openai_api_key"] = app_config.openai_api_key
    if not result.get("minimax_api_key"):
        result["minimax_api_key"] = app_config.minimax_api_key
    return result


def _build_llm(raw: dict) -> LLMService:
    return LLMService(
        provider=raw["llm_provider"],
        model=raw["llm_model"],
        anthropic_api_key=raw.get("anthropic_api_key", ""),
        openai_api_key=raw.get("openai_api_key", ""),
        minimax_api_key=raw.get("minimax_api_key", ""),
        ollama_base_url=raw.get("ollama_base_url") or app_config.ollama_base_url,
    )


def _contains_reasoning_markup(text: str) -> bool:
    lower = text.lower()
    return "<think>" in lower or "</think>" in lower


@router.get("")
async def get_settings(db: AsyncSession = Depends(get_db)):
    return await load_settings(db)


@router.patch("")
async def update_settings(body: dict, db: AsyncSession = Depends(get_db)):
    for key, value in body.items():
        # Never store a masked placeholder back — user didn't change the key
        if key in _SECRET_KEYS and _is_masked(str(value)):
            continue
        row = (await db.execute(select(AppSetting).where(AppSetting.key == key))).scalar_one_or_none()
        if row:
            row.value = str(value)
            row.updated_at = utcnow()
        else:
            db.add(AppSetting(key=key, value=str(value)))
    await db.commit()
    raw = await load_raw_settings(db)
    set_llm_service(_build_llm(raw))
    return await load_settings(db)


@router.get("/health")
async def settings_health(db: AsyncSession = Depends(get_db)):
    raw = await load_raw_settings(db)
    provider = raw["llm_provider"]
    model = raw["llm_model"]

    # Determine which key is needed for the active provider
    key_for_provider = {
        "anthropic": raw.get("anthropic_api_key", ""),
        "openai": raw.get("openai_api_key", ""),
        "minimax": raw.get("minimax_api_key", ""),
        "ollama": "local",  # no key needed
    }.get(provider, "")

    key_configured = bool(key_for_provider)

    steps = []
    total_tokens = 0
    total_cost = 0.0
    overall = "ok"

    # Build a fresh LLM service for the test so token counts are isolated
    test_llm = _build_llm(raw)
    test_llm.reset_session()

    def record(name: str, status: str, detail: str, latency_ms: int = 0):
        steps.append({"name": name, "status": status, "detail": detail, "latency_ms": latency_ms})

    # Step 0: key presence check (no network call)
    if not key_configured and provider != "ollama":
        record("API key", "error", f"No {provider} API key configured. Add it in Settings.")
        return {
            "overall": "error",
            "provider": provider,
            "model": model,
            "key_configured": False,
            "steps": steps,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "total_latency_ms": 0,
        }

    record("API key", "ok", f"Key is {'configured' if provider != 'ollama' else 'not required (local)'}.")

    # Step 1: Basic connectivity — simple one-word response
    t0 = time.monotonic()
    try:
        reply = await test_llm.complete(
            "You are a test assistant.",
            "Reply with the single word OK and nothing else.",
            max_tokens=40,
            temperature=0,
        )
        latency = int((time.monotonic() - t0) * 1000)
        if "ok" in reply.strip().lower():
            record("Connectivity", "ok", f"Received valid response from {model}.", latency)
        elif _contains_reasoning_markup(reply):
            record(
                "Connectivity",
                "warning",
                "Model emitted reasoning markup before the final answer. JSON tasks may still work, but non-reasoning models are more reliable.",
                latency,
            )
        else:
            record("Connectivity", "warning", f"Unexpected reply: {reply[:80]!r}", latency)
    except Exception as e:
        latency = int((time.monotonic() - t0) * 1000)
        record("Connectivity", "error", _friendly_error(e), latency)
        overall = "error"

    if overall == "error":
        stats = test_llm.get_session_stats()
        return _result(overall, provider, model, key_configured, steps, stats)

    # Step 2: JSON compliance — critical for the whole pipeline
    t0 = time.monotonic()
    try:
        raw_json = await test_llm.complete(
            'Return ONLY valid JSON. No markdown, no explanation.',
            'Return this exact structure: {"status": "ok", "value": 42}',
            max_tokens=200,
            temperature=0,
        )
        latency = int((time.monotonic() - t0) * 1000)
        parsed = test_llm._parse_json(raw_json)
        if parsed.get("status") == "ok":
            record("JSON output", "ok", "Model returns valid, parseable JSON.", latency)
        else:
            record("JSON output", "warning", f"JSON parsed but unexpected shape: {raw_json[:80]}", latency)
    except Exception as e:
        latency = int((time.monotonic() - t0) * 1000)
        msg = str(e)
        if "empty response" in msg.lower() or "invalid json" in msg.lower():
            detail = (
                f"{msg}. This model is not reliably returning plain JSON. "
                "Use a non-reasoning model or disable thinking, then run Test connection again."
            )
        else:
            detail = f"Could not parse JSON: {e}. Pipeline will fail without this."
        record("JSON output", "error", detail, latency)
        overall = "error"

    if overall == "error":
        stats = test_llm.get_session_stats()
        return _result(overall, provider, model, key_configured, steps, stats)

    # Step 3: Relevance scoring on a known topical article
    t0 = time.monotonic()
    try:
        res = await test_llm.check_topic_relevance(
            "OpenAI releases GPT-5 with improved reasoning capabilities",
            "OpenAI has announced GPT-5, its latest large language model featuring "
            "significant improvements in multi-step reasoning, code generation, and "
            "reduced hallucination rates compared to GPT-4.",
            "Artificial intelligence",
            "Artificial intelligence, machine learning, AI companies, and AI policy.",
        )
        latency = int((time.monotonic() - t0) * 1000)
        score = float(res.get("topic_relevance_score", res.get("ai_relevance_score", 0)))
        if score >= 0.8:
            record("Relevance scoring", "ok", f"Topic article scored {score:.2f} (expected >= 0.80).", latency)
        elif score >= 0.4:
            record("Relevance scoring", "warning",
                   f"Score {score:.2f} is low for an obviously relevant article and may filter too aggressively.", latency)
        else:
            record("Relevance scoring", "error",
                   f"Score {score:.2f} is far too low and will drop valid articles.", latency)
            overall = "degraded"
    except Exception as e:
        latency = int((time.monotonic() - t0) * 1000)
        msg = str(e)
        if "reasoning text instead of a final json answer" in msg.lower():
            detail = (
                "check_topic_relevance failed because the model emitted reasoning text instead of JSON. "
                "Refresh can still run, but topic relevance scoring will degrade until you switch to a non-reasoning model."
            )
        else:
            detail = f"check_topic_relevance failed: {e}"
        record("Relevance scoring", "error", detail, latency)
        overall = "degraded"

    # Step 4: Full article analysis — the most demanding pipeline call
    t0 = time.monotonic()
    try:
        processed = await test_llm.process_item(
            title="Anthropic releases Claude 4 with extended context window",
            url="https://example.com/anthropic-claude-4",
            source_name="TechCrunch",
            body=(
                "Anthropic today announced Claude 4, the latest iteration of its Claude "
                "large language model family. The new model features a 200K token context "
                "window, improved instruction following, and reduced hallucination rates. "
                "Enterprise pricing starts at $15 per million input tokens. The model is "
                "available immediately via the Anthropic API and will be integrated into "
                "Amazon Bedrock and Google Cloud Vertex AI next month."
            ),
            topic_name="Artificial intelligence",
            topic_description="Artificial intelligence, machine learning, AI companies, and AI policy.",
            known_vendors=["OpenAI", "Google", "Meta"],
            known_verticals=["Research", "Model releases", "Enterprise AI"],
        )
        latency = int((time.monotonic() - t0) * 1000)
        issues = []
        if not processed.summary:
            issues.append("no summary")
        if not processed.why_it_matters:
            issues.append("no why_it_matters")
        if not processed.vendor_tags:
            issues.append("no vendor tags")
        if processed.importance_rank < 1 or processed.importance_rank > 10:
            issues.append(f"importance_rank {processed.importance_rank} out of range")
        if issues:
            record("Article analysis", "warning",
                   f"Processed but missing fields: {', '.join(issues)}.", latency)
        else:
            record("Article analysis", "ok",
                   f"Summary, tags, pros/cons, and importance rank all generated. "
                   f"Vendors detected: {[v['name'] for v in processed.vendor_tags]}.", latency)
    except Exception as e:
        latency = int((time.monotonic() - t0) * 1000)
        msg = str(e)
        if "reasoning text instead of a final json answer" in msg.lower():
            detail = (
                "process_item failed because the model emitted reasoning text instead of JSON. "
                "Use a non-reasoning model or disable thinking before running Refresh."
            )
        else:
            detail = f"process_item failed: {e}"
        record("Article analysis", "error", detail, latency)
        if overall == "ok":
            overall = "degraded"

    stats = test_llm.get_session_stats()
    return _result(overall, provider, model, key_configured, steps, stats)


def _result(overall, provider, model, key_configured, steps, stats):
    total_ms = sum(s["latency_ms"] for s in steps)
    return {
        "overall": overall,
        "provider": provider,
        "model": model,
        "key_configured": key_configured,
        "steps": steps,
        "total_tokens": stats["tokens_in"] + stats["tokens_out"],
        "tokens_in": stats["tokens_in"],
        "tokens_out": stats["tokens_out"],
        "estimated_cost_usd": stats["estimated_cost_usd"],
        "llm_calls": stats["calls"],
        "total_latency_ms": total_ms,
    }


def _friendly_error(e: Exception) -> str:
    msg = str(e)
    if "401" in msg or "authentication" in msg.lower() or "api key" in msg.lower() or "invalid_api_key" in msg.lower():
        return "Authentication failed — API key is invalid or expired."
    if "403" in msg:
        return "Access denied — check your account has API access enabled."
    if "429" in msg or "rate_limit" in msg.lower():
        return "Rate limit hit — too many requests. Try again in a moment."
    if "model_not_found" in msg.lower() or "does not exist" in msg.lower():
        return f"Model not found — check the model name is correct."
    if "connection" in msg.lower() or "connect" in msg.lower():
        return "Connection failed — is the API endpoint reachable?"
    return msg[:200]

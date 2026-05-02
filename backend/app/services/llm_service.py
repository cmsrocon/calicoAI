import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from json import JSONDecodeError

logger = logging.getLogger(__name__)

_JSON_INSTRUCTION = "\n\nReturn ONLY valid JSON. No markdown, no explanation outside the JSON."
_NO_REASONING_INSTRUCTION = (
    "\nDo not output hidden reasoning, chain-of-thought, analysis, or <think> tags. "
    "Skip directly to the final answer."
)

# USD per 1M tokens (input, output) — update as pricing changes
_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-7": (15.0, 75.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (0.80, 4.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
    "gpt-4o": (2.50, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4": (30.0, 60.0),
    "gpt-3.5-turbo": (0.50, 1.50),
}


@dataclass
class ProcessedItem:
    headline: str
    language: str
    summary: str
    why_it_matters: str
    importance_rank: int
    pros: list[str]
    cons: list[str]
    balanced_take: str
    vendor_tags: list[dict]   # [{name, confidence}]
    vertical_tags: list[dict]  # [{name, confidence}]
    new_vendors: list[str]


class LLMService:
    _MINIMAX_BASE_URL = "https://api.minimaxi.chat/v1"
    _OLLAMA_BASE_URL = "http://localhost:11434/v1"

    def __init__(self, provider: str, model: str, anthropic_api_key: str = "", openai_api_key: str = "",
                 minimax_api_key: str = "", ollama_base_url: str = "", usage_tracker=None):
        self.provider = provider
        self.model = model
        self._anthropic_key = anthropic_api_key
        self._openai_key = openai_api_key
        self._minimax_key = minimax_api_key
        self._ollama_base_url = ollama_base_url or self._OLLAMA_BASE_URL
        self._usage_tracker = usage_tracker
        self._anthropic_client = None
        self._openai_client = None
        self._minimax_client = None
        self._ollama_client = None
        # Session-level usage tracking (reset per ingestion run)
        self._session_calls: int = 0
        self._session_tokens_in: int = 0
        self._session_tokens_out: int = 0

    def reset_session(self) -> None:
        self._session_calls = 0
        self._session_tokens_in = 0
        self._session_tokens_out = 0

    def get_session_stats(self) -> dict:
        cost = self._estimate_cost(self._session_tokens_in, self._session_tokens_out)
        return {
            "calls": self._session_calls,
            "tokens_in": self._session_tokens_in,
            "tokens_out": self._session_tokens_out,
            "estimated_cost_usd": round(cost, 6),
        }

    def fork(self, usage_tracker=None) -> "LLMService":
        return LLMService(
            provider=self.provider,
            model=self.model,
            anthropic_api_key=self._anthropic_key,
            openai_api_key=self._openai_key,
            minimax_api_key=self._minimax_key,
            ollama_base_url=self._ollama_base_url,
            usage_tracker=usage_tracker,
        )

    def _estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        pricing = _PRICING.get(self.model, (3.0, 15.0))
        return (tokens_in / 1_000_000 * pricing[0] + tokens_out / 1_000_000 * pricing[1])

    async def _before_call(self, max_tokens: int) -> None:
        if self._usage_tracker is not None:
            await self._usage_tracker.before_call(max_tokens)

    async def _record_usage(self, tokens_in: int, tokens_out: int) -> None:
        if self._usage_tracker is not None:
            await self._usage_tracker.record_call(
                self.model,
                tokens_in,
                tokens_out,
                round(self._estimate_cost(tokens_in, tokens_out), 6),
            )

    def _get_anthropic(self):
        if self._anthropic_client is None:
            import anthropic
            self._anthropic_client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        return self._anthropic_client

    def _get_openai(self):
        if self._openai_client is None:
            import openai
            self._openai_client = openai.AsyncOpenAI(api_key=self._openai_key)
        return self._openai_client

    def _get_minimax(self):
        if self._minimax_client is None:
            import openai
            self._minimax_client = openai.AsyncOpenAI(
                api_key=self._minimax_key,
                base_url=self._MINIMAX_BASE_URL,
            )
        return self._minimax_client

    def _get_ollama(self):
        if self._ollama_client is None:
            import openai
            # Ollama's OpenAI-compatible endpoint requires a non-empty key string
            self._ollama_client = openai.AsyncOpenAI(
                api_key="ollama",
                base_url=self._ollama_base_url,
            )
        return self._ollama_client

    async def complete(self, system: str, user: str, max_tokens: int = 1500, temperature: float = 0.2) -> str:
        for attempt in range(3):
            try:
                if self.provider == "anthropic":
                    return await self._complete_anthropic(system, user, max_tokens, temperature)
                elif self.provider == "minimax":
                    return await self._complete_openai_compat(self._get_minimax(), system, user, max_tokens, temperature)
                elif self.provider == "ollama":
                    return await self._complete_openai_compat(self._get_ollama(), system, user, max_tokens, temperature)
                else:
                    return await self._complete_openai_compat(self._get_openai(), system, user, max_tokens, temperature)
            except Exception as e:
                if attempt == 2:
                    raise
                wait = 2 ** attempt
                logger.warning(f"LLM attempt {attempt + 1} failed: {e}. Retrying in {wait}s.")
                await asyncio.sleep(wait)
        raise RuntimeError("LLM call failed after 3 attempts")

    async def _complete_anthropic(self, system: str, user: str, max_tokens: int, temperature: float) -> str:
        await self._before_call(max_tokens)
        client = self._get_anthropic()
        msg = await client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        self._session_calls += 1
        self._session_tokens_in += msg.usage.input_tokens
        self._session_tokens_out += msg.usage.output_tokens
        await self._record_usage(msg.usage.input_tokens, msg.usage.output_tokens)
        return msg.content[0].text

    async def _complete_openai_compat(self, client, system: str, user: str, max_tokens: int, temperature: float) -> str:
        await self._before_call(max_tokens)
        resp = await client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        self._session_calls += 1
        if resp.usage:
            self._session_tokens_in += resp.usage.prompt_tokens
            self._session_tokens_out += resp.usage.completion_tokens
            await self._record_usage(resp.usage.prompt_tokens, resp.usage.completion_tokens)
        content = resp.choices[0].message.content or ""
        cleaned = self._strip_reasoning_blocks(content)
        return cleaned or content

    def _strip_reasoning_blocks(self, text: str) -> str:
        stripped = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        return stripped.strip()

    def _parse_json(self, text: str) -> dict | list:
        payload = self._extract_json_payload(text)
        try:
            return json.loads(payload)
        except JSONDecodeError as exc:
            snippet = payload[:200].replace("\n", " ")
            raise ValueError(f"LLM returned invalid JSON: {snippet!r}") from exc

    def _extract_json_payload(self, text: str) -> str:
        payload = self._strip_reasoning_blocks(text) or text.strip()
        if not payload:
            raise ValueError(
                "LLM returned an empty response. Check the configured provider/model in Settings and run Test connection."
            )

        lower_payload = payload.lower()
        if lower_payload.startswith("<think>") and "{" not in payload and "[" not in payload:
            raise ValueError(
                "LLM returned reasoning text instead of a final JSON answer. "
                "Use a non-reasoning model or disable thinking in the selected model."
            )

        if payload.startswith("```"):
            lines = payload.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            payload = "\n".join(lines).strip()
            if not payload:
                raise ValueError(
                    "LLM returned an empty fenced response. Check the configured provider/model in Settings and run Test connection."
                )

        for start_char, end_char in (("{", "}"), ("[", "]")):
            start = payload.find(start_char)
            end = payload.rfind(end_char)
            if start == -1 or end == -1 or end <= start:
                continue
            candidate = payload[start:end + 1].strip()
            try:
                json.loads(candidate)
                return candidate
            except JSONDecodeError:
                continue

        return payload

    async def check_topic_relevance(self, title: str, body_snippet: str, topic_name: str, topic_description: str = "") -> dict:
        system = (
            f"You are a classifier for the news topic '{topic_name}'. Evaluate whether the given article "
            f"is meaningfully relevant to this topic. Topic scope: {topic_description or topic_name}."
            + _NO_REASONING_INSTRUCTION + _JSON_INSTRUCTION
        )
        user = (
            f"Title: {title}\n\nSnippet: {body_snippet[:500]}"
            "\n\nReturn: {\"is_topic_relevant\": bool, \"topic_relevance_score\": 0.0-1.0, \"reason\": \"string\"}"
        )
        raw = await self.complete(system, user, max_tokens=350, temperature=0.1)
        return self._parse_json(raw)

    async def process_item(
        self,
        title: str,
        url: str,
        source_name: str,
        body: str,
        topic_name: str,
        topic_description: str,
        known_vendors: list[str],
        known_verticals: list[str],
        source_documents: list[dict] | None = None,
    ) -> ProcessedItem:
        vendors_hint = ", ".join(known_vendors[:100]) if known_vendors else "none yet"
        verticals_hint = ", ".join(known_verticals[:100]) if known_verticals else "none yet"
        source_documents = source_documents or []
        source_bundle = json.dumps(source_documents[:8], indent=2) if source_documents else "[]"
        multi_source_guidance = (
            "You are distilling multiple source documents covering the same underlying story into a single canonical article. "
            "Capture the shared facts once, then make any differences in framing, interpretation, or opinion explicit in the balanced_take "
            "and in the pros/cons bullets. Preserve a balanced view and do not collapse disagreements into false consensus. "
            if len(source_documents) > 1 else
            ""
        )
        system = (
            f"You are an analyst for the topic '{topic_name}'. Process the provided article and return a structured analysis. "
            f"Topic scope: {topic_description or topic_name}. "
            + multi_source_guidance +
            "Be precise, factual, and balanced. For vendor tags, treat them as key entities such as organisations, people, teams, "
            "parties, or products central to the story. Prefer names from the known entities list when applicable. "
            "For vertical tags, treat them as concise recurring themes or subtopics. Reuse known theme names when they fit, "
            "but create a better one if needed."
            + _NO_REASONING_INSTRUCTION + _JSON_INSTRUCTION
        )
        user = f"""Title: {title}
URL: {url}
Source: {source_name}
Topic: {topic_name}
Source documents:
{source_bundle}

Article text:
{body}

Known entities (use these names when applicable): {vendors_hint}
Known themes (reuse when appropriate): {verticals_hint}

Return JSON:
{{
  "headline": "concise cleaned headline (max 120 chars)",
  "language": "2-letter ISO code",
  "summary": "3-4 sentence factual summary of the distilled story",
  "why_it_matters": "2-3 sentences on strategic significance",
  "importance_rank": 1-10,
  "pros": ["benefit, favorable claim, or positive interpretation from the coverage"],
  "cons": ["risk, criticism, or skeptical interpretation from the coverage"],
  "balanced_take": "nuanced synthesis paragraph that explicitly notes any disagreement or difference in perspective across sources",
  "vendor_tags": [{{"name": "Entity Name", "confidence": 0.0-1.0}}],
  "vertical_tags": [{{"name": "Theme Name", "confidence": 0.0-1.0}}],
  "new_vendors": ["important entity names not already in the known list"]
}}"""
        raw = await self.complete(system, user, max_tokens=1500, temperature=0.2)
        data = self._parse_json(raw)
        return ProcessedItem(
            headline=data.get("headline", title)[:120],
            language=data.get("language", "en"),
            summary=data.get("summary", ""),
            why_it_matters=data.get("why_it_matters", ""),
            importance_rank=max(1, min(10, int(data.get("importance_rank", 5)))),
            pros=data.get("pros", []),
            cons=data.get("cons", []),
            balanced_take=data.get("balanced_take", ""),
            vendor_tags=data.get("vendor_tags", []),
            vertical_tags=data.get("vertical_tags", []),
            new_vendors=data.get("new_vendors", []),
        )

    async def describe_vendor(self, name: str, context: str = "") -> dict:
        system = (
            "You are a researcher building a database of recurring news entities such as companies, people, "
            "teams, political parties, public institutions, and products. "
            "Provide accurate, factual descriptions." + _NO_REASONING_INSTRUCTION + _JSON_INSTRUCTION
        )
        user = f"""Vendor name: {name}
Context from article: {context[:500]}

Return JSON:
{{
  "name": "canonical company name",
  "description": "2-3 sentence description of this entity and why it matters",
  "aliases": ["alternative name 1", "ticker symbol"]
}}"""
        raw = await self.complete(system, user, max_tokens=400, temperature=0.3)
        return self._parse_json(raw)

    async def check_duplicates(self, pairs: list[tuple[str, str, str, str]]) -> list[dict]:
        """pairs: list of (title_a, url_a, title_b, url_b). Returns [{keep_url, discard_url}]."""
        if not pairs:
            return []
        items_json = json.dumps([{"title_a": a, "url_a": ua, "title_b": b, "url_b": ub} for a, ua, b, ub in pairs])
        system = (
            "You are a news deduplication system. Identify which pairs cover the same underlying story."
            + _NO_REASONING_INSTRUCTION + _JSON_INSTRUCTION
        )
        user = f"""Candidate pairs:
{items_json}

Return JSON array of duplicates (only pairs that ARE the same story):
[{{"keep_url": "url_to_keep", "discard_url": "url_to_discard", "reason": "brief reason"}}]

If no pairs are duplicates, return an empty array: []"""
        raw = await self.complete(system, user, max_tokens=500, temperature=0.1)
        result = self._parse_json(raw)
        return result if isinstance(result, list) else []

    async def analyze_trends(self, entity_name: str, items: list[dict], topic_name: str | None = None) -> dict:
        items_json = json.dumps(items[:30], indent=2)
        system = (
            "You are a news trends analyst. Analyze the batch of news items and identify "
            "key developments, trajectories, and emerging patterns. Be balanced and grounded in the data."
            + _NO_REASONING_INSTRUCTION + _JSON_INSTRUCTION
        )
        user = f"""Entity: {entity_name}
Topic scope: {topic_name or "All topics"}

News items (last 7 days):
{items_json}

Return JSON:
{{
  "narrative": "multi-paragraph trend analysis (2-4 paragraphs)",
  "sentiment_score": -1.0 to 1.0,
  "top_themes": ["theme 1", "theme 2", "theme 3"]
}}"""
        raw = await self.complete(system, user, max_tokens=2000, temperature=0.5)
        return self._parse_json(raw)

    async def analyze_overall_trends(self, items: list[dict], topic_name: str | None = None) -> dict:
        items_json = json.dumps(items[:40], indent=2)
        system = (
            "You are a news analyst writing a weekly overview. Synthesize developments "
            "across the selected topic into a clear, balanced narrative."
            + _NO_REASONING_INSTRUCTION + _JSON_INSTRUCTION
        )
        user = f"""Topic scope: {topic_name or "All topics"}

Top news items this period:
{items_json}

Return JSON:
{{
  "narrative": "3-5 paragraph industry overview",
  "sentiment_score": -1.0 to 1.0,
  "top_themes": ["cross-cutting theme 1", "theme 2", "theme 3", "theme 4"]
}}"""
        raw = await self.complete(system, user, max_tokens=2500, temperature=0.5)
        return self._parse_json(raw)

    async def suggest_topic_sources(self, topic_name: str, topic_description: str = "") -> list[dict]:
        system = (
            "You are building a trusted news source list for a topic-focused news monitoring app. "
            "Prefer reliable, established publications and topic-specialist outlets with real RSS feeds where possible. "
            "Do not invent URLs. If unsure, omit the source."
            + _NO_REASONING_INSTRUCTION + _JSON_INSTRUCTION
        )
        user = f"""Topic: {topic_name}
Description: {topic_description or topic_name}

Return a JSON array with 6 to 10 high-quality sources:
[
  {{
    "name": "Publication name",
    "url": "direct RSS or feed URL",
    "feed_type": "rss or html",
    "trust_weight": 0.5-2.0,
    "css_selector": "optional CSS selector or null"
  }}
]
"""
        raw = await self.complete(system, user, max_tokens=1200, temperature=0.2)
        data = self._parse_json(raw)
        return data if isinstance(data, list) else []


# Module-level singleton, initialized in main.py lifespan
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    if _llm_service is None:
        raise RuntimeError("LLM service not initialized")
    return _llm_service


def set_llm_service(service: LLMService) -> None:
    global _llm_service
    _llm_service = service

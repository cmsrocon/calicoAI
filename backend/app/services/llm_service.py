import asyncio
import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_JSON_INSTRUCTION = "\n\nReturn ONLY valid JSON. No markdown, no explanation outside the JSON."

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
                 minimax_api_key: str = "", ollama_base_url: str = ""):
        self.provider = provider
        self.model = model
        self._anthropic_key = anthropic_api_key
        self._openai_key = openai_api_key
        self._minimax_key = minimax_api_key
        self._ollama_base_url = ollama_base_url or self._OLLAMA_BASE_URL
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
        pricing = _PRICING.get(self.model, (3.0, 15.0))
        cost = (self._session_tokens_in / 1_000_000 * pricing[0] +
                self._session_tokens_out / 1_000_000 * pricing[1])
        return {
            "calls": self._session_calls,
            "tokens_in": self._session_tokens_in,
            "tokens_out": self._session_tokens_out,
            "estimated_cost_usd": round(cost, 6),
        }

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
        return msg.content[0].text

    async def _complete_openai_compat(self, client, system: str, user: str, max_tokens: int, temperature: float) -> str:
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
        return resp.choices[0].message.content or ""

    def _parse_json(self, text: str) -> dict | list:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(text)

    async def check_relevance(self, title: str, body_snippet: str) -> dict:
        system = (
            "You are a classifier for AI industry news. Evaluate whether the given article "
            "is meaningfully related to artificial intelligence, machine learning, LLMs, AI companies, "
            "AI policy, or AI applications in industry." + _JSON_INSTRUCTION
        )
        user = f"Title: {title}\n\nSnippet: {body_snippet[:500]}\n\nReturn: {{\"is_ai_relevant\": bool, \"ai_relevance_score\": 0.0-1.0, \"reason\": \"string\"}}"
        raw = await self.complete(system, user, max_tokens=200, temperature=0.1)
        return self._parse_json(raw)

    async def process_item(self, title: str, url: str, source_name: str, body: str,
                           known_vendors: list[str], known_verticals: list[str]) -> ProcessedItem:
        vendors_hint = ", ".join(known_vendors[:100]) if known_vendors else "none yet"
        verticals_list = ", ".join(known_verticals)
        system = (
            "You are an expert AI industry analyst. Process the provided article and return a structured analysis. "
            "Be precise, factual, and balanced. For vendor tags, prefer names from the known vendors list. "
            f"For verticals, choose ONLY from this list: {verticals_list}." + _JSON_INSTRUCTION
        )
        user = f"""Title: {title}
URL: {url}
Source: {source_name}

Article text:
{body}

Known vendors (use these names when applicable): {vendors_hint}

Return JSON:
{{
  "headline": "concise cleaned headline (max 120 chars)",
  "language": "2-letter ISO code",
  "summary": "3-4 sentence factual summary",
  "why_it_matters": "2-3 sentences on strategic significance",
  "importance_rank": 1-10,
  "pros": ["advantage 1", "advantage 2"],
  "cons": ["risk or concern 1"],
  "balanced_take": "nuanced synthesis paragraph",
  "vendor_tags": [{{"name": "Vendor Name", "confidence": 0.0-1.0}}],
  "vertical_tags": [{{"name": "Vertical Name", "confidence": 0.0-1.0}}],
  "new_vendors": ["any vendor names not in the known list that are important AI players"]
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
            "You are a researcher building a database of AI industry players. "
            "Provide accurate, factual descriptions." + _JSON_INSTRUCTION
        )
        user = f"""Vendor name: {name}
Context from article: {context[:500]}

Return JSON:
{{
  "name": "canonical company name",
  "description": "2-3 sentence description of this company's role in AI",
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
            "You are a news deduplication system. Identify which pairs cover the same underlying story." + _JSON_INSTRUCTION
        )
        user = f"""Candidate pairs:
{items_json}

Return JSON array of duplicates (only pairs that ARE the same story):
[{{"keep_url": "url_to_keep", "discard_url": "url_to_discard", "reason": "brief reason"}}]

If no pairs are duplicates, return an empty array: []"""
        raw = await self.complete(system, user, max_tokens=500, temperature=0.1)
        result = self._parse_json(raw)
        return result if isinstance(result, list) else []

    async def analyze_trends(self, entity_name: str, items: list[dict]) -> dict:
        items_json = json.dumps(items[:30], indent=2)
        system = (
            "You are an AI industry trends analyst. Analyze the batch of news items and identify "
            "key developments, trajectories, and emerging patterns. Be balanced and grounded in the data." + _JSON_INSTRUCTION
        )
        user = f"""Entity: {entity_name}

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

    async def analyze_overall_trends(self, items: list[dict]) -> dict:
        items_json = json.dumps(items[:40], indent=2)
        system = (
            "You are an AI industry analyst writing a weekly overview. Synthesize developments "
            "across vendors and sectors into a clear, balanced narrative." + _JSON_INSTRUCTION
        )
        user = f"""Top AI news items this period:
{items_json}

Return JSON:
{{
  "narrative": "3-5 paragraph industry overview",
  "sentiment_score": -1.0 to 1.0,
  "top_themes": ["cross-cutting theme 1", "theme 2", "theme 3", "theme 4"]
}}"""
        raw = await self.complete(system, user, max_tokens=2500, temperature=0.5)
        return self._parse_json(raw)


# Module-level singleton, initialized in main.py lifespan
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    if _llm_service is None:
        raise RuntimeError("LLM service not initialized")
    return _llm_service


def set_llm_service(service: LLMService) -> None:
    global _llm_service
    _llm_service = service

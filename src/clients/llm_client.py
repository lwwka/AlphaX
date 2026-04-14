from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from src.utils.cache import get_cache, make_cache_key, set_cache


class LLMClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
        sentiment_model: str,
        report_model: str,
        cache_dir: str,
        provider: str = "openrouter",
    ) -> None:
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout_seconds)
        self.sentiment_model = sentiment_model
        self.report_model = report_model
        self.cache_dir = cache_dir
        self.provider = provider

    def score_sentiment_batch(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not items:
            return []

        payload = {"model": self.sentiment_model, "items": items, "task": "sentiment_batch_v1"}
        cache_key = make_cache_key(payload)
        cached = get_cache(cache_key, self.cache_dir)
        if cached is not None:
            return cached  # type: ignore[return-value]

        system_prompt = (
            "You score tweet sentiment for listed securities. "
            "Return strict JSON array only. "
            "Each item must include: tweet_id, symbol, score, label, rationale, signal_type. "
            "score must be between -1.0 and 1.0. rationale must be short."
        )
        user_prompt = json.dumps(items, ensure_ascii=False)
        response = self.client.chat.completions.create(
            model=self.sentiment_model,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or "[]"
        parsed = _parse_json_array(content)
        set_cache(cache_key, parsed, self.cache_dir)
        return parsed

    def generate_report_summary(self, context: dict[str, Any]) -> str:
        payload = {"model": self.report_model, "context": context, "task": "daily_report_summary_v1"}
        cache_key = make_cache_key(payload)
        cached = get_cache(cache_key, self.cache_dir)
        if cached is not None and isinstance(cached, dict):
            return str(cached.get("summary", ""))

        system_prompt = (
            "You are writing a concise market signal summary. "
            "Do not invent data. Use a neutral research tone. "
            "Return plain markdown only."
        )
        response = self.client.chat.completions.create(
            model=self.report_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
        )
        content = response.choices[0].message.content or ""
        set_cache(cache_key, {"summary": content}, self.cache_dir)
        return content


def _parse_json_array(content: str) -> list[dict[str, Any]]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    data = json.loads(stripped)
    if not isinstance(data, list):
        raise RuntimeError("Expected JSON array from sentiment model")
    return data

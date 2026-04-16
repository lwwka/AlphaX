from __future__ import annotations

from typing import Any

from src.clients.llm_client import LLMClient
from src.models.schemas import AccountConfig, EntityMatch, SentimentResult, TweetRecord


def score_sentiment(
    tweets: list[TweetRecord],
    entity_matches: dict[str, list[EntityMatch]],
    accounts: list[AccountConfig],
    settings: dict[str, Any],
    api_key: str,
    logger,
) -> list[SentimentResult]:
    llm_settings = settings["llm"]
    client = LLMClient(
        base_url=llm_settings["api_base_url"],
        api_key=api_key,
        timeout_seconds=int(llm_settings.get("timeout_seconds", 45)),
        sentiment_model=llm_settings["sentiment_model"],
        report_model=llm_settings["report_model"],
        cache_dir=settings["paths"]["cache_dir"],
        provider=llm_settings["provider"],
    )
    account_focus = {account.handle: account.focus for account in accounts}
    tweet_index = {tweet.tweet_id: tweet for tweet in tweets}
    source_weights = settings.get("tweet_source_weights", {})

    batch_items: list[dict[str, Any]] = []
    for tweet_id, matches in entity_matches.items():
        tweet = tweet_index.get(tweet_id)
        if tweet is None:
            continue
        source_type = tweet.source_type
        source_weight = _source_weight(source_type, source_weights)
        for match in matches:
            batch_items.append(
                {
                    "tweet_id": tweet.tweet_id,
                    "handle": tweet.handle,
                    "text": tweet.text[:800],
                    "symbol": match.symbol,
                    "match_type": match.match_type,
                    "focus": account_focus.get(tweet.handle, []),
                    "source_type": source_type,
                    "source_weight": source_weight,
                }
            )

    if not batch_items:
        return []

    try:
        raw_results = client.score_sentiment_batch(batch_items)
    except Exception as exc:
        logger.warning("sentiment model failed, marking analyses as failed: %s", exc)
        return [
            SentimentResult(
                tweet_id=item["tweet_id"],
                handle=item["handle"],
                symbol=item["symbol"],
                score=0.0,
                label="analysis_failed",
                rationale="LLM analysis failed; no model output was trusted.",
                signal_type="analysis_failed",
                provider=llm_settings["provider"],
                model=llm_settings["sentiment_model"],
                source_type=item["source_type"],
                source_weight=item["source_weight"],
            )
            for item in batch_items
        ]

    results: list[SentimentResult] = []
    for item, raw in zip(batch_items, raw_results):
        score = _clamp_score(raw.get("score", 0.0))
        results.append(
            SentimentResult(
                tweet_id=item["tweet_id"],
                handle=item["handle"],
                symbol=item["symbol"],
                score=score,
                label=str(raw.get("label", _label_from_score(score))),
                rationale=str(raw.get("rationale", "")).strip()[:280],
                signal_type=str(raw.get("signal_type", "generic")),
                provider=llm_settings["provider"],
                model=llm_settings["sentiment_model"],
                source_type=item["source_type"],
                source_weight=item["source_weight"],
            )
        )
    return results


def _clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    return max(-1.0, min(1.0, score))


def _label_from_score(score: float) -> str:
    if score >= 0.3:
        return "bullish"
    if score <= -0.3:
        return "bearish"
    return "neutral"


def _source_weight(source_type: str, weights: dict[str, Any]) -> float:
    try:
        return float(weights.get(source_type, weights.get("original", 1.0)))
    except (TypeError, ValueError):
        return 1.0

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markdown import markdown

from src.clients.llm_client import LLMClient
from src.models.schemas import PriceSnapshot, SentimentResult, SignalResult, TweetRecord
from src.utils.io import write_text


def build_daily_report(
    report_date: str,
    tweets: list[TweetRecord],
    sentiments: list[SentimentResult],
    signals: list[SignalResult],
    prices: dict[str, PriceSnapshot],
    settings: dict[str, Any],
    api_key: str | None,
    logger,
) -> dict[str, str]:
    summary = _build_summary(signals, sentiments, api_key, settings, logger)
    context = _build_context(report_date, tweets, sentiments, signals, prices, settings, summary)

    template_env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=select_autoescape(disabled_extensions=("j2",)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = template_env.get_template("daily_report.md.j2")
    markdown_content = template.render(**context)
    html_content = markdown(markdown_content, extensions=["tables", "fenced_code"])

    reports_dir = settings["paths"]["reports_dir"]
    md_path = f"{reports_dir}/daily_{report_date}.md"
    html_path = f"{reports_dir}/daily_{report_date}.html"
    write_text(md_path, markdown_content)
    write_text(html_path, html_content)
    return {"markdown": md_path, "html": html_path}


def _build_summary(
    signals: list[SignalResult],
    sentiments: list[SentimentResult],
    api_key: str | None,
    settings: dict[str, Any],
    logger,
) -> str:
    if not api_key or not signals:
        return "No LLM report summary was generated. Review the signal table and audit fields below."

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
    payload = {
        "signals": [asdict(item) for item in signals[:20]],
        "sentiments": [asdict(item) for item in sentiments[:20]],
    }
    try:
        return client.generate_report_summary(payload).strip()
    except Exception as exc:
        logger.warning("report model failed, using fallback summary: %s", exc)
        return "LLM report generation failed. The report below contains deterministic data and audit fields only."


def _build_context(
    report_date: str,
    tweets: list[TweetRecord],
    sentiments: list[SentimentResult],
    signals: list[SignalResult],
    prices: dict[str, PriceSnapshot],
    settings: dict[str, Any],
    summary: str,
) -> dict[str, Any]:
    tweet_index = {tweet.tweet_id: tweet for tweet in tweets}
    sentiment_index = {(item.tweet_id, item.symbol): item for item in sentiments}

    details: list[dict[str, Any]] = []
    for signal in signals:
        tweet = tweet_index.get(signal.tweet_id)
        sentiment = sentiment_index.get((signal.tweet_id, signal.symbol))
        price = prices.get(signal.symbol)
        if tweet is None or sentiment is None or price is None:
            continue
        details.append(
            {
                "symbol": signal.symbol,
                "signal": signal.signal,
                "handle": signal.handle,
                "tweet_text": tweet.text,
                "tweet_time": tweet.created_at.isoformat(),
                "sentiment_score": sentiment.score,
                "sentiment_label": sentiment.label,
                "rationale": sentiment.rationale,
                "signal_type": sentiment.signal_type,
                "price_close": price.close,
                "price_change_pct": round(price.change_pct, 3),
                "volume": price.volume,
                "avg_20d_volume": round(price.avg_20d_volume, 2),
                "price_source": price.source,
                "account_weight": signal.account_weight,
                "volume_factor": round(signal.volume_factor, 2),
                "price_confirmed": signal.price_confirmed,
                "explain": signal.explain,
            }
        )

    signal_rows = [
        {
            "symbol": item.symbol,
            "signal": item.signal,
            "score": round(item.final_score, 3),
            "trigger": f"@{item.handle}",
        }
        for item in signals
    ]
    return {
        "report_date": report_date,
        "summary": summary,
        "signal_rows": signal_rows,
        "details": details,
        "provider": settings["llm"]["provider"],
        "sentiment_model": settings["llm"]["sentiment_model"],
        "report_model": settings["llm"]["report_model"],
    }

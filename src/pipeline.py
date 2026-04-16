from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.collectors.price_collector import collect_prices
from src.collectors.tweet_collector import collect_recent_tweets
from src.processors.entity_mapper import map_tweet_entities
from src.processors.sentiment import score_sentiment
from src.processors.signal_engine import build_signals
from src.reporting.report_builder import build_daily_report
from src.utils.config_loader import load_accounts, load_entity_map, load_settings, read_required_env
from src.utils.io import write_json
from src.utils.logger import setup_logger


def run_daily_pipeline(run_date: str | None = None) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "config" / "settings.yaml")
    accounts = load_accounts(root / "config" / "accounts.yaml")
    entity_map = load_entity_map(root / "config" / "entity_map.yaml")

    selected_date = run_date or date.today().isoformat()
    settings["_run_date"] = selected_date
    run_id = f"{selected_date}-{uuid4().hex[:8]}"
    logger = setup_logger("alphax", root / settings["paths"]["logs_dir"], run_id)

    twitter_key = read_required_env(settings["twitter"]["api_key_env"])
    llm_key = read_required_env(settings["llm"]["api_key_env"])
    logger.info("starting run_id=%s provider=%s", run_id, settings["llm"]["provider"])

    with _project_root(root):
        tweets = collect_recent_tweets(accounts, settings, twitter_key, logger)

        entity_matches: dict[str, list] = defaultdict(list)
        for tweet in tweets:
            entity_matches[tweet.tweet_id].extend(map_tweet_entities(tweet, entity_map))

        tracked_symbols = {match.symbol for matches in entity_matches.values() for match in matches}
        markets = settings.get("markets", {})
        tracked_symbols.update(markets.get("watchlist", []))
        tracked_symbols.update(markets.get("benchmarks", []))
        prices = collect_prices(list(tracked_symbols), settings, logger)

        sentiments = score_sentiment(tweets, entity_matches, accounts, settings, llm_key, logger)
        signals = build_signals(sentiments, prices, accounts, settings)

        write_json(Path(settings["paths"]["sentiment_dir"]) / f"{selected_date}.json", sentiments)
        write_json(Path(settings["paths"]["signals_dir"]) / f"{selected_date}.json", signals)

        report_paths = build_daily_report(
            report_date=selected_date,
            tweets=tweets,
            sentiments=sentiments,
            signals=signals,
            prices=prices,
            settings=settings,
            api_key=llm_key,
            logger=logger,
        )

    logger.info(
        "completed run_id=%s tweets=%s sentiments=%s signals=%s",
        run_id,
        len(tweets),
        len(sentiments),
        len(signals),
    )
    return {
        "run_id": run_id,
        "generated_at": datetime.utcnow().isoformat(),
        "tweets": len(tweets),
        "sentiments": len(sentiments),
        "signals": len(signals),
        "report_paths": report_paths,
        "provider": settings["llm"]["provider"],
        "sentiment_model": settings["llm"]["sentiment_model"],
        "report_model": settings["llm"]["report_model"],
        "signals_preview": [asdict(item) for item in signals[:10]],
    }


class _project_root:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.previous = Path.cwd()

    def __enter__(self) -> None:
        import os

        os.chdir(self.root)

    def __exit__(self, exc_type, exc, tb) -> None:
        import os

        os.chdir(self.previous)

from __future__ import annotations

import re
from typing import Any

from src.models.schemas import EntityMatch, TweetRecord

TICKER_REGEX = re.compile(r"\$([A-Z]{1,5}(?:\.HK)?)\b")


def map_tweet_entities(tweet: TweetRecord, entity_map: dict[str, Any]) -> list[EntityMatch]:
    matches: list[EntityMatch] = []
    seen_symbols: set[str] = set()

    for symbol in TICKER_REGEX.findall(tweet.text):
        normalized = symbol if symbol.endswith(".HK") else symbol.upper()
        seen_symbols.add(normalized)
        matches.append(
            EntityMatch(
                tweet_id=tweet.tweet_id,
                symbol=normalized,
                market="UNKNOWN",
                match_type="ticker_regex",
                keyword=f"${normalized}",
                confidence=0.99,
            )
        )

    for rule in entity_map.get("rules", []):
        keyword = str(rule["keyword"])
        if keyword.lower() not in tweet.text.lower():
            continue
        symbol = str(rule["symbol"])
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        matches.append(
            EntityMatch(
                tweet_id=tweet.tweet_id,
                symbol=symbol,
                market=str(rule.get("market", "UNKNOWN")),
                match_type="keyword_rule",
                keyword=keyword,
                confidence=float(rule.get("confidence", 0.8)),
            )
        )
    return matches

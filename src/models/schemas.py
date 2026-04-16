from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class AccountConfig:
    handle: str
    user_id: str
    weight: float
    focus: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TweetRecord:
    tweet_id: str
    handle: str
    user_id: str
    text: str
    created_at: datetime
    source_type: str = "original"
    lang: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EntityMatch:
    tweet_id: str
    symbol: str
    market: str
    match_type: str
    keyword: str
    confidence: float


@dataclass(slots=True)
class PriceSnapshot:
    symbol: str
    as_of: datetime
    close: float
    change_pct: float
    volume: float
    avg_20d_volume: float
    source: str


@dataclass(slots=True)
class SentimentResult:
    tweet_id: str
    handle: str
    symbol: str
    score: float
    label: str
    rationale: str
    signal_type: str
    provider: str
    model: str
    source_type: str = "original"
    source_weight: float = 1.0


@dataclass(slots=True)
class SignalResult:
    tweet_id: str
    handle: str
    symbol: str
    sentiment_score: float
    final_score: float
    signal: str
    account_weight: float
    source_type: str
    source_weight: float
    volume_factor: float
    price_confirmed: bool
    explain: str

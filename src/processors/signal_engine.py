from __future__ import annotations

from src.models.schemas import AccountConfig, PriceSnapshot, SentimentResult, SignalResult


def build_signals(
    sentiments: list[SentimentResult],
    prices: dict[str, PriceSnapshot],
    accounts: list[AccountConfig],
    settings: dict,
) -> list[SignalResult]:
    thresholds = settings["thresholds"]
    rules = settings["signal_rules"]
    account_weights = {account.handle: account.weight for account in accounts}
    signals: list[SignalResult] = []

    for sentiment in sentiments:
        if sentiment.label == "analysis_failed":
            continue

        price = prices.get(sentiment.symbol)
        if price is None:
            continue

        weight = float(account_weights.get(sentiment.handle, 1.0))
        volume_spike_flag = 1 if _volume_spike(price, rules["volume_trigger_ratio"]) else 0
        volume_factor = 1 + (float(rules["volume_boost"]) * volume_spike_flag)
        raw_score = max(-1.0, min(1.0, sentiment.score * weight * volume_factor))
        price_confirmed = _price_confirms(raw_score, price.change_pct)
        signal = _classify_signal(raw_score, price_confirmed, thresholds, rules)
        explain = (
            f"raw_score={sentiment.score:.3f} * weight={weight:.2f} * volume_factor={volume_factor:.2f} "
            f"=> final={raw_score:.3f}; price_confirmed={price_confirmed}"
        )
        signals.append(
            SignalResult(
                tweet_id=sentiment.tweet_id,
                handle=sentiment.handle,
                symbol=sentiment.symbol,
                sentiment_score=sentiment.score,
                final_score=raw_score,
                signal=signal,
                account_weight=weight,
                volume_factor=volume_factor,
                price_confirmed=price_confirmed,
                explain=explain,
            )
        )
    return signals


def _volume_spike(price: PriceSnapshot, trigger_ratio: float) -> bool:
    if price.avg_20d_volume <= 0:
        return False
    return (price.volume / price.avg_20d_volume) >= float(trigger_ratio)


def _price_confirms(score: float, change_pct: float) -> bool:
    if score > 0:
        return change_pct > 0
    if score < 0:
        return change_pct < 0
    return False


def _classify_signal(score: float, price_confirmed: bool, thresholds: dict, rules: dict) -> str:
    require_confirmation = bool(rules.get("require_price_confirmation_for_strong", True))
    if score >= float(thresholds["strong_buy"]) and (price_confirmed or not require_confirmation):
        return "強力買入"
    if score >= float(thresholds["buy"]):
        return "買入"
    if score <= float(thresholds["strong_sell"]) and (price_confirmed or not require_confirmation):
        return "強力賣出"
    if score <= float(thresholds["sell"]):
        return "賣出"
    return "觀察"

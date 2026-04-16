from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any

from src.clients.twitterapi_client import TwitterApiClient
from src.models.schemas import AccountConfig, TweetRecord
from src.utils.io import read_json, write_json


def collect_recent_tweets(
    accounts: list[AccountConfig],
    settings: dict[str, Any],
    api_key: str,
    logger,
) -> list[TweetRecord]:
    twitter_settings = settings["twitter"]
    client = TwitterApiClient(
        base_url=twitter_settings["api_base_url"],
        api_key=api_key,
        timeout_seconds=int(twitter_settings.get("timeout_seconds", 20)),
        max_retries=int(twitter_settings.get("max_retries", 3)),
        min_request_interval_seconds=float(twitter_settings.get("min_request_interval_seconds", 5)),
    )

    lookback_hours = int(twitter_settings.get("lookback_hours", 24))
    max_pages_per_account = int(twitter_settings.get("max_pages_per_account", 1))
    include_replies = bool(twitter_settings.get("include_replies", False))
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=lookback_hours)
    state_path = Path(settings["paths"].get("twitter_state_path", f'{settings["paths"]["cache_dir"]}/twitter_state.json'))
    state = _load_twitter_state(state_path)
    records: list[TweetRecord] = []
    raw_payload: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    updated_state = dict(state)

    for account in accounts:
        account_state = state.get(account.handle, {})
        last_seen_id = str(account_state.get("last_seen_tweet_id") or "")
        last_seen_at = _parse_datetime(account_state.get("last_seen_created_at")) if account_state.get("last_seen_created_at") else None
        fetch_start_time = max(start_time, last_seen_at or start_time)

        try:
            tweets = client.fetch_user_tweets(
                account.user_id,
                account.handle,
                fetch_start_time,
                end_time,
                include_replies=include_replies,
                max_pages=max_pages_per_account,
                stop_at_tweet_id=last_seen_id or None,
            )
        except Exception as exc:
            logger.warning("tweet fetch failed for @%s: %s", account.handle, exc)
            continue

        newest_tweet: TweetRecord | None = None
        for item in tweets:
            raw_payload.append({"account": account.handle, "tweet": item})
            tweet = _normalize_tweet(item, account)
            if tweet is None or tweet.tweet_id in seen_ids:
                continue
            if _is_already_seen(tweet, last_seen_id, last_seen_at):
                continue
            seen_ids.add(tweet.tweet_id)
            records.append(tweet)
            if newest_tweet is None or tweet.created_at > newest_tweet.created_at:
                newest_tweet = tweet

        if newest_tweet is not None:
            updated_state[account.handle] = {
                "user_id": account.user_id,
                "last_seen_tweet_id": newest_tweet.tweet_id,
                "last_seen_created_at": newest_tweet.created_at.isoformat(),
                "updated_at": end_time.isoformat(),
            }
        elif account.handle not in updated_state:
            updated_state[account.handle] = {
                "user_id": account.user_id,
                "last_seen_tweet_id": last_seen_id,
                "last_seen_created_at": last_seen_at.isoformat() if last_seen_at else None,
                "updated_at": end_time.isoformat(),
            }

    output_path = f'{settings["paths"]["raw_tweets_dir"]}/{end_time.date().isoformat()}.json'
    write_json(output_path, raw_payload)
    write_json(state_path, updated_state)
    logger.info("collected %s tweets", len(records))
    return records


def _load_twitter_state(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = read_json(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_already_seen(tweet: TweetRecord, last_seen_id: str, last_seen_at: datetime | None) -> bool:
    if last_seen_at is None:
        return False
    if tweet.created_at < last_seen_at:
        return True
    if tweet.created_at == last_seen_at and last_seen_id and tweet.tweet_id == last_seen_id:
        return True
    return False


def _normalize_tweet(raw: dict[str, Any], account: AccountConfig) -> TweetRecord | None:
    source_type = _classify_source_type(raw)
    text = _extract_business_text(raw, source_type)
    if not text:
        return None

    created_value = raw.get("createdAt") or raw.get("created_at")
    created_at = _parse_datetime(created_value)
    tweet_id = str(raw.get("id") or raw.get("tweet_id") or "")
    if not tweet_id:
        return None

    metrics = {
        "like_count": raw.get("likeCount") or raw.get("favorite_count") or 0,
        "retweet_count": raw.get("retweetCount") or raw.get("retweet_count") or 0,
        "reply_count": raw.get("replyCount") or raw.get("reply_count") or 0,
    }
    return TweetRecord(
        tweet_id=tweet_id,
        handle=account.handle,
        user_id=account.user_id,
        text=text,
        created_at=created_at,
        source_type=source_type,
        lang=raw.get("lang"),
        metrics=metrics,
    )


def _classify_source_type(raw: dict[str, Any]) -> str:
    if raw.get("retweeted_tweet") or raw.get("isRetweet") or raw.get("retweeted"):
        return "retweet"
    if raw.get("quoted_tweet"):
        return "quote"
    if raw.get("isReply") or raw.get("inReplyToStatusId") or raw.get("inReplyToId"):
        return "reply"
    text = str(raw.get("text") or raw.get("full_text") or "").strip()
    if text.startswith("RT @"):
        return "retweet"
    return "original"


def _extract_business_text(raw: dict[str, Any], source_type: str) -> str:
    if source_type == "retweet" and isinstance(raw.get("retweeted_tweet"), dict):
        retweeted = raw["retweeted_tweet"]
        author = retweeted.get("author") or {}
        user_name = author.get("userName") or author.get("screen_name") or "unknown"
        text = str(retweeted.get("text") or retweeted.get("full_text") or "").strip()
        return f"RT @{user_name}: {text}" if text else ""

    text = str(raw.get("text") or raw.get("full_text") or "").strip()
    if source_type == "quote" and isinstance(raw.get("quoted_tweet"), dict):
        quoted = raw["quoted_tweet"]
        quoted_author = quoted.get("author") or {}
        user_name = quoted_author.get("userName") or quoted_author.get("screen_name") or "unknown"
        quoted_text = str(quoted.get("text") or quoted.get("full_text") or "").strip()
        if quoted_text:
            return f"{text}\n\nQuoted @{user_name}: {quoted_text}".strip()
    return text


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.now(timezone.utc)
    text = str(value).strip()

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.strptime(text, "%a %b %d %H:%M:%S %z %Y")

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed

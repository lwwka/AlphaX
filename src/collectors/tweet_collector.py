from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from src.clients.twitterapi_client import TwitterApiClient
from src.models.schemas import AccountConfig, TweetRecord
from src.utils.io import write_json


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
    )

    lookback_hours = int(twitter_settings.get("lookback_hours", 24))
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=lookback_hours)
    records: list[TweetRecord] = []
    raw_payload: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for account in accounts:
        try:
            tweets = client.fetch_user_tweets(account.user_id, start_time, end_time)
        except Exception as exc:
            logger.warning("tweet fetch failed for @%s: %s", account.handle, exc)
            continue

        for item in tweets:
            raw_payload.append({"account": account.handle, "tweet": item})
            tweet = _normalize_tweet(item, account)
            if tweet is None or tweet.tweet_id in seen_ids:
                continue
            seen_ids.add(tweet.tweet_id)
            records.append(tweet)

    output_path = f'{settings["paths"]["raw_tweets_dir"]}/{end_time.date().isoformat()}.json'
    write_json(output_path, raw_payload)
    logger.info("collected %s tweets", len(records))
    return records


def _normalize_tweet(raw: dict[str, Any], account: AccountConfig) -> TweetRecord | None:
    text = str(raw.get("text") or raw.get("full_text") or "").strip()
    if not text:
        return None
    if raw.get("isRetweet") or raw.get("retweeted"):
        return None
    if raw.get("isReply") or raw.get("inReplyToStatusId"):
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
        lang=raw.get("lang"),
        metrics=metrics,
    )


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.now(timezone.utc)
    text = str(value).replace("Z", "+00:00")
    return datetime.fromisoformat(text)

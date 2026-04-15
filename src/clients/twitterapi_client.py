from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic, sleep
from typing import Any

import httpx


class TwitterApiClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
        max_retries: int,
        min_request_interval_seconds: float = 0.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.min_request_interval_seconds = max(0.0, float(min_request_interval_seconds))
        self._last_request_at = 0.0

    def fetch_user_tweets(
        self,
        user_id: str,
        user_name: str | None,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        headers = {"X-API-Key": self.api_key}
        params: dict[str, Any] = {"includeReplies": "false"}
        if user_id:
            params["userId"] = user_id
        elif user_name:
            params["userName"] = user_name
        else:
            raise RuntimeError("twitter account is missing both user_id and user_name")

        tweets: list[dict[str, Any]] = []
        cursor = ""
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            while True:
                response = self._get_with_retry(
                    client,
                    "/twitter/user/last_tweets",
                    headers=headers,
                    params={**params, "cursor": cursor},
                )
                payload = response.json()
                page = self._extract_tweets(payload)
                tweets.extend(
                    tweet
                    for tweet in page
                    if start_time <= self._parse_created_at(tweet.get("createdAt")) <= end_time
                )

                has_next_page = bool(payload.get("has_next_page"))
                next_cursor = str(payload.get("next_cursor") or "").strip()
                if not has_next_page or not next_cursor:
                    break
                if page and all(self._parse_created_at(tweet.get("createdAt")) < start_time for tweet in page):
                    break
                cursor = next_cursor
        return tweets

    def _get_with_retry(self, client: httpx.Client, path: str, headers: dict[str, str], params: dict[str, Any]) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            response = client.get(path, headers=headers, params=params)
            if response.status_code != 429:
                response.raise_for_status()
                return response

            retry_after = self._read_retry_after(response)
            last_error = RuntimeError(
                f"twitterapi.io rate limited request (429). waited {retry_after:.1f}s before retry {attempt}/{self.max_retries}"
            )
            if attempt == self.max_retries:
                break
            sleep(retry_after)

        raise last_error or RuntimeError("twitterapi.io request failed after retries")

    def _throttle(self) -> None:
        if self.min_request_interval_seconds <= 0:
            self._last_request_at = monotonic()
            return

        now = monotonic()
        elapsed = now - self._last_request_at
        remaining = self.min_request_interval_seconds - elapsed
        if remaining > 0:
            sleep(remaining)
        self._last_request_at = monotonic()

    def _read_retry_after(self, response: httpx.Response) -> float:
        header_value = response.headers.get("Retry-After")
        if header_value:
            try:
                return max(float(header_value), self.min_request_interval_seconds, 1.0)
            except ValueError:
                pass
        return max(self.min_request_interval_seconds, 5.0)

    def _extract_tweets(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            tweets = payload
        elif isinstance(payload, dict):
            status = str(payload.get("status") or "").lower()
            if status == "error":
                message = payload.get("message") or payload.get("msg") or "twitterapi.io returned an error"
                raise RuntimeError(str(message))

            data = payload.get("data")
            tweets = payload.get("tweets")
            if tweets is None and isinstance(data, dict):
                tweets = data.get("tweets")
            if tweets is None and isinstance(data, list):
                tweets = data
        else:
            tweets = None

        if not isinstance(tweets, list):
            raise RuntimeError(f"Unexpected twitterapi.io response format: {type(payload).__name__}")
        return tweets

    @staticmethod
    def _parse_created_at(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if not value:
            return datetime.min.replace(tzinfo=timezone.utc)
        text = str(value).strip()

        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            parsed = datetime.strptime(text, "%a %b %d %H:%M:%S %z %Y")

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

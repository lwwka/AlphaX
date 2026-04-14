from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class TwitterApiClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: int, max_retries: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def fetch_user_tweets(
        self,
        user_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        headers = {"X-API-Key": self.api_key}
        params = {
            "userId": user_id,
            "startDate": start_time.isoformat(),
            "endDate": end_time.isoformat(),
        }
        with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds) as client:
            response = client.get("/twitter/user/last_tweets", headers=headers, params=params)
            response.raise_for_status()
        payload = response.json()
        tweets = payload.get("tweets") or payload.get("data") or []
        if not isinstance(tweets, list):
            raise RuntimeError("Unexpected twitterapi.io response format")
        return tweets

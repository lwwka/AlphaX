from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.schemas import TweetRecord
from src.processors.entity_mapper import map_tweet_entities
from src.utils.config_loader import load_entity_map


def main() -> int:
    parser = argparse.ArgumentParser(description="Test entity mapping against sample tweet text.")
    parser.add_argument("text", help="Tweet text to evaluate")
    args = parser.parse_args()

    entity_map = load_entity_map(ROOT / "config" / "entity_map.yaml")
    fake_tweet = TweetRecord(
        tweet_id="manual-test",
        handle="tester",
        user_id="0",
        text=args.text,
        created_at=datetime.now(timezone.utc),
    )
    matches = map_tweet_entities(fake_tweet, entity_map)
    for match in matches:
        print(
            f"symbol={match.symbol} market={match.market} "
            f"match_type={match.match_type} keyword={match.keyword} confidence={match.confidence}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_daily_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill AlphaX daily artifacts.")
    parser.add_argument("--from", dest="from_date", required=True, help="Start date in YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", required=True, help="End date in YYYY-MM-DD")
    args = parser.parse_args()

    current = date.fromisoformat(args.from_date)
    end = date.fromisoformat(args.to_date)
    while current <= end:
        run_daily_pipeline(current.isoformat())
        current += timedelta(days=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

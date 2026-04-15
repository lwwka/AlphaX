# AlphaX

AlphaX is a transparent market signal research assistant that tracks selected X accounts,
maps tweets to listed symbols, scores sentiment with low-cost LLM models through OpenRouter,
and generates auditable daily reports.

## Features

- Track configurable X accounts from `config/accounts.yaml`
- Map tweet text to US / HK symbols using regex and keyword rules
- Pull market data from `yfinance` with `akshare` as HK fallback
- Score sentiment with OpenRouter-hosted models
- Calculate rule-based signals with clear audit fields
- Render Markdown and HTML daily reports

## Setup

1. Go into the project folder:

```bash
cd /YourFolder/AlphaX
```

2. Recreate the virtual environment with Python 3.12:

```bash
rm -rf .venv
python3.12 -m venv .venv
source .venv/bin/activate
```

3. Upgrade `pip` and install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Required keys:

- `TWITTERAPI_IO_API_KEY`
- `OPENROUTER_API_KEY`

5. Adjust configs under `config/` if needed.
6. Run the daily pipeline:

```bash
python scripts/run_daily.py
```

Generated reports are written to `data/reports/` in `md`, `html`, `csv`, `xlsx`, and `docx` formats.
The report summary is also written in a more natural research-note style so it is easier to share with non-technical readers.
Reports now include extra analysis sections such as executive takeaway, key drivers, caveats, and next-day watch items.

To reduce Twitter API cost, the default config limits each account to `1` page per run and stores `last_seen` state in `data/cache/twitter_state.json` for incremental fetching.

## Notes

- This tool is not investment advice.
- Signals are algorithmic outputs and should be independently verified.
- LLM failures degrade safely to `analysis_failed` instead of fabricating signals.

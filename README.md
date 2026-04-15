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

## Notes

- This tool is not investment advice.
- Signals are algorithmic outputs and should be independently verified.
- LLM failures degrade safely to `analysis_failed` instead of fabricating signals.

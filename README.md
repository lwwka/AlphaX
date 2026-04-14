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

1. Create a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your API keys.
4. Adjust configs under `config/`.
5. Run the daily pipeline:

```bash
python scripts/run_daily.py
```

## Notes

- This tool is not investment advice.
- Signals are algorithmic outputs and should be independently verified.
- LLM failures degrade safely to `analysis_failed` instead of fabricating signals.

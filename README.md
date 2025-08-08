# NSE News & Fundamentals Trading System

This repository implements a local, zero‑cost pipeline for Indian equities. It
collects annual reports and daily India‑focused news, filters them with
`gpt-4o-mini`, and backtests a simple VWAP strategy.

## Layout

```
repo/
 ├─ data/                # cached PDFs, raw news, prices
 ├─ pipelines/
 │    ├─ fetch_reports.py
 │    ├─ fetch_news.py
 │    ├─ gpt_filter.py
 │    └─ backtest.py
 ├─ config.py            # API keys, paths, constants
 ├─ requirements.txt
 └─ README.md
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="..."
python pipelines/fetch_reports.py --ticker TCS
python pipelines/fetch_news.py --ticker TCS --company "Tata Consultancy Services"
python pipelines/gpt_filter.py --ticker TCS --company "Tata Consultancy Services"
python pipelines/backtest.py --ticker TCS --company "Tata Consultancy Services"
```

The outputs are written under `data/<ticker>/` as `reports.json`, daily news
JSONs, `signals.parquet`, `trades.csv`, and `performance.html`.

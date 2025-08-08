"""Download and parse annual reports/fundamentals for an NSE ticker."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import requests
from prefect import flow, task

from config import DATA_DIR

HEADERS = {"User-Agent": "Mozilla/5.0"}


@task
def fetch_fundamentals(ticker: str) -> Dict[str, Dict[str, float]]:
    """Fetch last three fiscal years of key fundamentals from Screener API."""
    url = f"https://www.screener.in/api/company/{ticker}/"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # Structure: data['data']['financials']['Profit & Loss']['yearly']
    pl = data["data"]["financials"]["Profit & Loss"]["yearly"]
    bs = data["data"]["financials"]["Balance Sheet"]["yearly"]

    years = sorted(pl.keys())[-3:]  # last 3 fiscal years
    metrics: Dict[str, Dict[str, float]] = {}
    for year in years:
        metrics[year] = {
            "revenue": pl[year].get("Sales"),
            "ebitda": pl[year].get("Operating Profit"),
            "pat": pl[year].get("Net Profit"),
            "debt": bs[year].get("Borrowings"),
            "cash": bs[year].get("Cash & Bank"),
        }
    return metrics


@task
def save_reports(ticker: str, metrics: Dict[str, Dict[str, float]]) -> Path:
    out_dir = DATA_DIR / ticker
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "reports.json"
    with out_file.open("w") as f:
        json.dump(metrics, f, indent=2)
    return out_file


@flow
def fetch_reports(ticker: str) -> Path:
    metrics = fetch_fundamentals(ticker)
    return save_reports(ticker, metrics)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    args = parser.parse_args()
    fetch_reports(args.ticker)

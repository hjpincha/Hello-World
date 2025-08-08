"""Fetch daily news for an NSE ticker from Google News and GDELT."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import feedparser
import requests
from newspaper import Article
import trafilatura
from prefect import flow, task

from config import DATA_DIR, DATE_FORMAT

HEADERS = {"User-Agent": "Mozilla/5.0"}


def _scrape(url: str) -> str:
    """Download and clean article text."""
    try:
        art = Article(url)
        art.download()
        art.parse()
        return art.text
    except Exception:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            return trafilatura.extract(downloaded, include_comments=False, include_tables=False) or ""
    return ""


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


@task
def fetch_google_news(ticker: str, company_name: str) -> List[Dict]:
    query = f"{company_name} OR {ticker} site:in"
    url = (
        "https://news.google.com/rss/search?q="
        + requests.utils.quote(query)
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )
    feed = feedparser.parse(url)
    articles: List[Dict] = []
    for entry in feed.entries:
        link = entry.link
        articles.append(
            {
                "title": entry.title,
                "url": link,
                "published": entry.published,
                "source": getattr(entry, "source", {}).get("title"),
                "text": _scrape(link),
                "hash": _hash_url(link),
            }
        )
    return articles


@task
def fetch_gdelt(ticker: str, company_name: str) -> List[Dict]:
    query = requests.utils.quote(f'"{company_name}" OR {ticker}')
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc?query="
        + query
        + "&mode=ArtList&format=json&maxrecords=50&sort=DateDesc"
    )
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    articles: List[Dict] = []
    for doc in data.get("articles", []):
        link = doc["url"]
        articles.append(
            {
                "title": doc.get("title"),
                "url": link,
                "published": doc.get("seendate"),
                "source": doc.get("sourceCommonName"),
                "text": _scrape(link),
                "hash": _hash_url(link),
            }
        )
    return articles


@task
def save_news(ticker: str, articles: List[Dict]) -> Path:
    date_str = datetime.utcnow().strftime(DATE_FORMAT)
    out_dir = DATA_DIR / ticker / "news"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{date_str}.json"
    with out_file.open("w") as f:
        json.dump(articles, f, indent=2)
    return out_file


@flow
def fetch_news(ticker: str, company_name: str) -> Path:
    google_articles = fetch_google_news(ticker, company_name)
    gdelt_articles = fetch_gdelt(ticker, company_name)
    seen = set()
    deduped: List[Dict] = []
    for art in google_articles + gdelt_articles:
        if art["hash"] not in seen:
            seen.add(art["hash"])
            deduped.append(art)
    return save_news(ticker, deduped)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--company", required=True, help="Full company name")
    args = parser.parse_args()
    fetch_news(args.ticker, args.company)

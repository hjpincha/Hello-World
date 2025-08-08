"""Classify scraped news using GPT-4o-mini."""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict

import pandas as pd
from openai import OpenAI
from prefect import flow, task

from config import DATA_DIR, OPENAI_API_KEY, OPENAI_MODEL


@task
def load_fundamentals(ticker: str) -> Dict:
    path = DATA_DIR / ticker / "reports.json"
    with path.open() as f:
        return json.load(f)


@task
def load_news_files(ticker: str) -> List[Path]:
    news_dir = DATA_DIR / ticker / "news"
    return sorted(news_dir.glob("*.json"))


@task
def classify_file(ticker: str, company: str, fundamentals: Dict, news_file: Path) -> pd.DataFrame:
    with news_file.open() as f:
        articles = json.load(f)
    if not articles:
        return pd.DataFrame()

    client = OpenAI(api_key=OPENAI_API_KEY)
    system_prompt = (
        "You are an equity-research analyst. Using the latest FY fundamentals: "
        + json.dumps(fundamentals)
        + "\nFor each article provided, output JSON list objects:\n"
        '{"relevance":0|1, "impact":"POS|NEG|NEU", "rationale":"25 words"}\n'
        "– relevance=1 only if the piece unambiguously refers to the company.\n"
        "– impact is POS if earnings or financing terms should improve in next 12 months; NEG if worsen."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(articles)},
    ]
    resp = client.chat.completions.create(model=OPENAI_MODEL, messages=messages)
    content = resp.choices[0].message.content
    try:
        classifications = json.loads(content)
    except Exception:
        # if parsing fails, mark all irrelevant
        classifications = [
            {"relevance": 0, "impact": "NEU", "rationale": "parse error"}
            for _ in articles
        ]

    rows = []
    for art, cls in zip(articles, classifications):
        rows.append(
            {
                "date": news_file.stem,
                "url": art["url"],
                "impact": cls.get("impact"),
                "relevance": cls.get("relevance"),
                "rationale": cls.get("rationale"),
            }
        )
    return pd.DataFrame(rows)


@task
def save_signals(ticker: str, df: pd.DataFrame) -> Path:
    out_file = DATA_DIR / ticker / "signals.parquet"
    if out_file.exists():
        old = pd.read_parquet(out_file)
        df = pd.concat([old, df], ignore_index=True)
    df.to_parquet(out_file, index=False)
    return out_file


@flow
def gpt_filter(ticker: str, company: str) -> Path:
    fundamentals = load_fundamentals(ticker)
    files = load_news_files(ticker)
    dfs = [classify_file(ticker, company, fundamentals, f) for f in files]
    df = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    return save_signals(ticker, df)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--company", required=True)
    args = parser.parse_args()
    gpt_filter(args.ticker, args.company)

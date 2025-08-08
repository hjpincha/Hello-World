"""Backtest simple news-driven strategy."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf
import empyrical as emp

from config import (
    DATA_DIR,
    POSITION_SIZE,
    TAKE_PROFIT,
    STOP_LOSS,
    MAX_HOLD_DAYS,
    COOL_OFF_DAYS,
)


def load_signals(ticker: str) -> pd.DataFrame:
    path = DATA_DIR / ticker / "signals.parquet"
    if path.exists():
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["impact"] == "POS"]
        df = df[df["relevance"] == 1]
        return df
    return pd.DataFrame(columns=["date", "url", "impact", "relevance", "rationale"])


def load_prices(ticker: str) -> pd.DataFrame:
    end = datetime.utcnow()
    start = end - timedelta(days=365 * 5)
    df = yf.download(ticker, start=start, end=end, progress=False)
    df.index = pd.to_datetime(df.index)
    df["typical"] = (df["High"] + df["Low"] + df["Close"]) / 3.0
    df["200dma"] = df["Close"].rolling(200).mean()
    return df


def backtest(ticker: str, signals: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    trades = []
    position = None
    cool_off = 0

    for date, row in prices.iterrows():
        if position:
            # check exit
            hold_days = (date - position["entry_date"]).days
            ret = (row["Close"] - position["entry_price"]) / position["entry_price"]
            if ret >= TAKE_PROFIT:
                trades.append({**position, "exit_date": date, "exit_price": row["Close"], "reason": "tp"})
                position = None
                cool_off = COOL_OFF_DAYS
            elif ret <= STOP_LOSS:
                trades.append({**position, "exit_date": date, "exit_price": row["Close"], "reason": "sl"})
                position = None
                cool_off = COOL_OFF_DAYS
            elif hold_days >= MAX_HOLD_DAYS:
                trades.append({**position, "exit_date": date, "exit_price": row["Close"], "reason": "time"})
                position = None
                cool_off = COOL_OFF_DAYS
        else:
            if cool_off > 0:
                cool_off -= 1
                continue
            signal_today = signals[signals["date"] == date]
            if not signal_today.empty and row["Close"] > row["200dma"]:
                # enter next day's VWAP (approx typical price of next day)
                next_idx = prices.index.get_loc(date) + 1
                if next_idx < len(prices):
                    next_row = prices.iloc[next_idx]
                    entry_price = next_row["typical"]
                    position = {"entry_date": prices.index[next_idx], "entry_price": entry_price}

    # close open position at end
    if position:
        last_row = prices.iloc[-1]
        trades.append({**position, "exit_date": prices.index[-1], "exit_price": last_row["Close"], "reason": "eod"})

    return pd.DataFrame(trades)


def evaluate(trades: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    equity = 1.0
    curve = []
    for _, t in trades.iterrows():
        ret = (t["exit_price"] - t["entry_price"]) / t["entry_price"]
        equity *= 1 + POSITION_SIZE * ret
        curve.append({"date": t["exit_date"], "equity": equity})
    curve_df = pd.DataFrame(curve).set_index("date")
    returns = curve_df["equity"].pct_change().dropna()
    metrics = {
        "CAGR": emp.annual_return(returns),
        "Sharpe": emp.sharpe_ratio(returns),
        "MaxDrawdown": emp.max_drawdown(returns.cumsum()),
    }
    return pd.DataFrame(metrics, index=[0])


def run_backtest(ticker: str) -> None:
    signals = load_signals(ticker)
    prices = load_prices(ticker)
    trades = backtest(ticker, signals, prices)
    out_dir = DATA_DIR / ticker
    out_dir.mkdir(exist_ok=True)
    trades.to_csv(out_dir / "trades.csv", index=False)
    perf = evaluate(trades, prices)
    perf.to_html(out_dir / "performance.html", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--company", required=True)
    args = parser.parse_args()
    run_backtest(args.ticker)

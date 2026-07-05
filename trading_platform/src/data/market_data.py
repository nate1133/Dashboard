from __future__ import annotations

import pandas as pd
import yfinance as yf

from trading_platform.src.data.indicators import add_indicators, normalize_ohlcv


def get_price_history(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    symbol = ticker.upper().strip()

    if not symbol:
        return pd.DataFrame()

    raw = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    return add_indicators(normalize_ohlcv(raw))


def get_latest_snapshot(tickers: list[str]) -> pd.DataFrame:
    rows = []

    for ticker in tickers:
        history = get_price_history(ticker, period="6mo")

        if history.empty:
            rows.append({"ticker": ticker, "status": "No data"})
            continue

        latest = history.iloc[-1]
        prior = history.iloc[-2] if len(history) > 1 else latest
        daily_change_pct = ((latest["close"] / prior["close"]) - 1) * 100 if prior["close"] else 0

        rows.append(
            {
                "ticker": ticker,
                "price": round(float(latest["close"]), 2),
                "daily_change_pct": round(float(daily_change_pct), 2),
                "volume": int(latest["volume"]) if pd.notna(latest["volume"]) else 0,
                "trend": latest_market_trend(history),
                "rsi_14": round(float(latest["rsi_14"]), 2) if pd.notna(latest["rsi_14"]) else None,
                "status": "OK",
            }
        )

    return pd.DataFrame(rows)


def latest_market_trend(history: pd.DataFrame) -> str:
    if history.empty or len(history) < 50:
        return "Unknown"

    latest = history.iloc[-1]

    if latest["close"] > latest.get("sma_50", float("inf")):
        return "Above 50D MA"

    return "Below 50D MA"

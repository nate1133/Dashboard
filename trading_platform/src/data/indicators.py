import numpy as np
import pandas as pd


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    output = df.copy()

    if isinstance(output.columns, pd.MultiIndex):
        output.columns = [column[0] for column in output.columns]

    rename_map = {
        "Date": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adjusted_close",
        "Volume": "volume",
    }

    output = output.reset_index().rename(columns=rename_map)

    if "date" not in output.columns and "Datetime" in output.columns:
        output = output.rename(columns={"Datetime": "date"})

    output.columns = [str(column).lower() for column in output.columns]

    if "adjusted_close" not in output.columns and "close" in output.columns:
        output["adjusted_close"] = output["close"]

    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output = output.dropna(subset=["date", "close"]).sort_values("date")

    return output


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    output = df.copy()
    close = output["close"]

    output["daily_return_pct"] = close.pct_change() * 100
    output["sma_20"] = close.rolling(20).mean()
    output["sma_50"] = close.rolling(50).mean()
    output["sma_200"] = close.rolling(200).mean()
    output["volume_sma_20"] = output["volume"].rolling(20).mean()
    output["volatility_20d_pct"] = output["daily_return_pct"].rolling(20).std() * np.sqrt(252)

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    output["rsi_14"] = 100 - (100 / (1 + rs))

    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    output["macd"] = ema_12 - ema_26
    output["macd_signal"] = output["macd"].ewm(span=9, adjust=False).mean()
    output["macd_histogram"] = output["macd"] - output["macd_signal"]

    output["52w_high"] = close.rolling(252, min_periods=1).max()
    output["52w_low"] = close.rolling(252, min_periods=1).min()

    return output


def classify_market_state(df: pd.DataFrame) -> str:
    if df.empty or len(df) < 50:
        return "Insufficient data"

    latest = df.iloc[-1]
    close = latest["close"]
    sma_20 = latest.get("sma_20")
    sma_50 = latest.get("sma_50")
    rsi = latest.get("rsi_14")

    if pd.notna(rsi) and rsi >= 70:
        return "Overbought"

    if pd.notna(rsi) and rsi <= 30:
        return "Oversold"

    if pd.notna(sma_20) and pd.notna(sma_50) and close > sma_20 > sma_50:
        return "Trending higher"

    if pd.notna(sma_20) and pd.notna(sma_50) and close < sma_20 < sma_50:
        return "Trending lower"

    return "Consolidating"

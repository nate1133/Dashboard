from pathlib import Path
import sys

import pandas as pd
import yfinance as yf
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TICKER_CONFIG_PATH = PROJECT_ROOT / "config" / "tickers.csv"

sys.path.insert(0, str(PROJECT_ROOT))

from app.db import create_db_engine, load_database_settings

print("Database settings loaded:")
db_settings = load_database_settings()
print(f"DB_USER={db_settings['DB_USER']}")
print(f"DB_HOST={db_settings['DB_HOST']}")
print(f"DB_PORT={db_settings['DB_PORT']}")
print(f"DB_NAME={db_settings['DB_NAME']}")

engine = create_db_engine()

def get_tickers():
    tickers_df = pd.read_csv(TICKER_CONFIG_PATH)
    tickers_df["ticker"] = tickers_df["ticker"].str.upper().str.strip()
    tickers = tickers_df["ticker"].dropna().unique().tolist()
    return tickers


def load_stock_data():
    all_rows = []
    tickers = get_tickers()

    for ticker in tickers:
        print(f"Downloading {ticker}...")

        df = yf.download(
            ticker,
            period="2y",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if df.empty:
            print(f"No data returned for {ticker}")
            continue

        df = df.reset_index()

        # Handle possible multi-index columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df["ticker"] = ticker

        df = df.rename(columns={
            "Date": "price_date",
            "Open": "open_price",
            "High": "high_price",
            "Low": "low_price",
            "Close": "close_price",
            "Adj Close": "adjusted_close",
            "Volume": "volume"
        })

        df = df[[
            "ticker",
            "price_date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "adjusted_close",
            "volume"
        ]]

        all_rows.append(df)

    if not all_rows:
        print("No data to load.")
        return

    final_df = pd.concat(all_rows, ignore_index=True)

    with engine.begin() as conn:
        for _, row in final_df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO finance_econ.stock_prices
                    (
                        ticker,
                        price_date,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        adjusted_close,
                        volume
                    )
                    VALUES
                    (
                        :ticker,
                        :price_date,
                        :open_price,
                        :high_price,
                        :low_price,
                        :close_price,
                        :adjusted_close,
                        :volume
                    )
                    ON CONFLICT (ticker, price_date)
                    DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        adjusted_close = EXCLUDED.adjusted_close,
                        volume = EXCLUDED.volume,
                        loaded_at = CURRENT_TIMESTAMP;
                """),
                row.to_dict()
            )

    print(f"Loaded {len(final_df)} rows into finance_econ.stock_prices.")

if __name__ == "__main__":
    load_stock_data()

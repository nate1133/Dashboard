from pathlib import Path
import sys

import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TICKER_CONFIG_PATH = PROJECT_ROOT / "config" / "tickers.csv"

sys.path.insert(0, str(PROJECT_ROOT))

from app.db import create_db_engine

engine = create_db_engine()


def load_ticker_metadata():
    df = pd.read_csv(TICKER_CONFIG_PATH)

    df["ticker"] = df["ticker"].str.upper().str.strip()
    df["name"] = df["name"].str.strip()
    df["category"] = df["category"].str.strip()

    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO finance_econ.ticker_metadata
                    (
                        ticker,
                        name,
                        category
                    )
                    VALUES
                    (
                        :ticker,
                        :name,
                        :category
                    )
                    ON CONFLICT (ticker)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        category = EXCLUDED.category,
                        loaded_at = CURRENT_TIMESTAMP;
                """),
                row.to_dict()
            )

    print(f"Loaded {len(df)} ticker metadata rows.")


if __name__ == "__main__":
    load_ticker_metadata()

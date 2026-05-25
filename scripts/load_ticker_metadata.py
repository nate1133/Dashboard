from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
TICKER_CONFIG_PATH = PROJECT_ROOT / "config" / "tickers.csv"

load_dotenv(ENV_PATH)

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


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

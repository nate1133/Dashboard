from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
INDICATOR_CONFIG_PATH = PROJECT_ROOT / "config" / "economic_indicators.csv"

load_dotenv(ENV_PATH)

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


def download_fred_indicator(indicator_code: str) -> pd.DataFrame:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={indicator_code}"

    df = pd.read_csv(url)

    # FRED files usually return columns like: observation_date, CPIAUCSL
    df = df.rename(columns={
        "observation_date": "observation_date",
        indicator_code: "value"
    })

    df["observation_date"] = pd.to_datetime(df["observation_date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["value"])

    return df[["observation_date", "value"]]


def load_economic_indicators():
    config_df = pd.read_csv(INDICATOR_CONFIG_PATH)

    config_df["indicator_code"] = config_df["indicator_code"].str.upper().str.strip()
    config_df["indicator_name"] = config_df["indicator_name"].str.strip()
    config_df["source"] = config_df["source"].str.strip()

    total_rows = 0

    with engine.begin() as conn:
        for _, indicator in config_df.iterrows():
            code = indicator["indicator_code"]
            name = indicator["indicator_name"]
            source = indicator["source"]

            print(f"Downloading {code} - {name}...")

            df = download_fred_indicator(code)

            if df.empty:
                print(f"No data returned for {code}")
                continue

            for _, row in df.iterrows():
                conn.execute(
                    text("""
                        INSERT INTO finance_econ.economic_indicators
                        (
                            indicator_code,
                            indicator_name,
                            observation_date,
                            value,
                            source
                        )
                        VALUES
                        (
                            :indicator_code,
                            :indicator_name,
                            :observation_date,
                            :value,
                            :source
                        )
                        ON CONFLICT (indicator_code, observation_date)
                        DO UPDATE SET
                            indicator_name = EXCLUDED.indicator_name,
                            value = EXCLUDED.value,
                            source = EXCLUDED.source,
                            loaded_at = CURRENT_TIMESTAMP;
                    """),
                    {
                        "indicator_code": code,
                        "indicator_name": name,
                        "observation_date": row["observation_date"],
                        "value": row["value"],
                        "source": source
                    }
                )

            total_rows += len(df)
            print(f"Loaded {len(df)} rows for {code}")

    print(f"Finished loading {total_rows} total economic indicator rows.")


if __name__ == "__main__":
    load_economic_indicators()

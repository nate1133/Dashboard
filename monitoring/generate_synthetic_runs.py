from pathlib import Path
import random
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import text


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT))

from app.db import create_db_engine

engine = create_db_engine()


PIPELINES = [
    {
        "pipeline_name": "stock_loader",
        "source_system": "Yahoo Finance",
        "expected_rows": 750,
        "normal_duration": 45,
    },
    {
        "pipeline_name": "macro_loader",
        "source_system": "FRED",
        "expected_rows": 4200,
        "normal_duration": 35,
    },
    {
        "pipeline_name": "ticker_metadata_loader",
        "source_system": "config_csv",
        "expected_rows": 15,
        "normal_duration": 5,
    },
]


ISSUE_TYPES = [
    "none",
    "stale_data",
    "missing_entities",
    "row_count_drop",
    "load_failure",
    "slow_load",
    "warning_spike",
]


def choose_issue_type() -> str:
    """
    Most runs should be healthy.
    Some runs should have issues so the model has something to learn.
    """
    return random.choices(
        ISSUE_TYPES,
        weights=[72, 8, 6, 6, 3, 3, 2],
        k=1
    )[0]


def build_run(run_date: datetime, pipeline: dict) -> dict:
    issue_type = choose_issue_type()

    pipeline_name = pipeline["pipeline_name"]
    source_system = pipeline["source_system"]
    expected_rows = pipeline["expected_rows"]
    normal_duration = pipeline["normal_duration"]

    run_start_time = run_date + timedelta(
        hours=random.choice([7, 8, 15, 16, 23]),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )

    duration_seconds = max(
        1,
        np.random.normal(normal_duration, normal_duration * 0.20)
    )

    rows_loaded = int(np.random.normal(expected_rows, expected_rows * 0.05))
    rows_loaded = max(rows_loaded, 0)

    missing_entity_count = 0
    error_count = 0
    warning_count = random.randint(0, 2)
    status = "success"
    issue_flag = 0
    latest_data_lag_days = random.choice([0, 0, 0, 1])
    notes = "Healthy run."

    if issue_type == "stale_data":
        issue_flag = 1
        latest_data_lag_days = random.randint(3, 10)
        warning_count += random.randint(1, 3)
        notes = "Latest data date appears stale."

    elif issue_type == "missing_entities":
        issue_flag = 1
        missing_entity_count = random.randint(1, 8)
        rows_loaded = max(0, rows_loaded - missing_entity_count * random.randint(20, 80))
        warning_count += random.randint(2, 5)
        notes = "Some expected tickers or indicators were missing."

    elif issue_type == "row_count_drop":
        issue_flag = 1
        rows_loaded = int(expected_rows * random.uniform(0.0, 0.45))
        warning_count += random.randint(1, 4)
        notes = "Rows loaded dropped sharply below expected count."

    elif issue_type == "load_failure":
        issue_flag = 1
        status = "failed"
        rows_loaded = 0
        error_count = random.randint(1, 4)
        warning_count += random.randint(1, 3)
        duration_seconds = random.uniform(2, 15)
        latest_data_lag_days = random.randint(2, 12)
        notes = "Pipeline failed during execution."

    elif issue_type == "slow_load":
        issue_flag = 1
        duration_seconds = normal_duration * random.uniform(3, 8)
        warning_count += random.randint(1, 3)
        notes = "Pipeline took much longer than normal."

    elif issue_type == "warning_spike":
        issue_flag = 1
        warning_count = random.randint(8, 20)
        notes = "Warning count was unusually high."

    else:
        issue_type = None

    row_count_difference = rows_loaded - expected_rows

    if expected_rows:
        row_count_pct_difference = round(row_count_difference / expected_rows * 100, 4)
    else:
        row_count_pct_difference = 0

    expected_latest_date = run_start_time.date()

    latest_data_date = expected_latest_date - timedelta(days=latest_data_lag_days)

    run_end_time = run_start_time + timedelta(seconds=float(duration_seconds))

    # Simple synthetic score: 100 is best, lower is worse.
    data_quality_score = 100
    data_quality_score -= min(abs(row_count_pct_difference), 50)
    data_quality_score -= missing_entity_count * 3
    data_quality_score -= error_count * 15
    data_quality_score -= warning_count * 2
    data_quality_score -= latest_data_lag_days * 5
    data_quality_score = max(0, round(data_quality_score, 2))

    return {
        "pipeline_name": pipeline_name,
        "source_system": source_system,
        "run_start_time": run_start_time,
        "run_end_time": run_end_time,
        "status": status,
        "issue_flag": issue_flag,
        "issue_type": issue_type,
        "rows_loaded": rows_loaded,
        "expected_rows": expected_rows,
        "row_count_difference": row_count_difference,
        "row_count_pct_difference": row_count_pct_difference,
        "latest_data_date": latest_data_date,
        "expected_latest_date": expected_latest_date,
        "latest_data_lag_days": latest_data_lag_days,
        "missing_entity_count": missing_entity_count,
        "error_count": error_count,
        "warning_count": warning_count,
        "duration_seconds": round(float(duration_seconds), 2),
        "data_quality_score": data_quality_score,
        "notes": notes,
    }


def generate_runs(num_days: int = 365) -> pd.DataFrame:
    today = datetime.now()
    rows = []

    for day_offset in range(num_days):
        run_date = today - timedelta(days=day_offset)

        for pipeline in PIPELINES:
            # Stock loader mostly runs weekdays
            if pipeline["pipeline_name"] == "stock_loader" and run_date.weekday() >= 5:
                continue

            # Macro loader mostly runs Mondays
            if pipeline["pipeline_name"] == "macro_loader" and run_date.weekday() != 0:
                continue

            rows.append(build_run(run_date, pipeline))

    df = pd.DataFrame(rows)
    df = df.sort_values("run_start_time").reset_index(drop=True)
    return df


def load_runs_to_postgres(df: pd.DataFrame) -> None:
    insert_sql = text("""
        INSERT INTO pipeline_monitoring.pipeline_runs
        (
            pipeline_name,
            source_system,
            run_start_time,
            run_end_time,
            status,
            issue_flag,
            issue_type,
            rows_loaded,
            expected_rows,
            row_count_difference,
            row_count_pct_difference,
            latest_data_date,
            expected_latest_date,
            latest_data_lag_days,
            missing_entity_count,
            error_count,
            warning_count,
            duration_seconds,
            data_quality_score,
            notes
        )
        VALUES
        (
            :pipeline_name,
            :source_system,
            :run_start_time,
            :run_end_time,
            :status,
            :issue_flag,
            :issue_type,
            :rows_loaded,
            :expected_rows,
            :row_count_difference,
            :row_count_pct_difference,
            :latest_data_date,
            :expected_latest_date,
            :latest_data_lag_days,
            :missing_entity_count,
            :error_count,
            :warning_count,
            :duration_seconds,
            :data_quality_score,
            :notes
        );
    """)

    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(insert_sql, row.to_dict())


def main():
    print("Generating synthetic pipeline runs...")
    df = generate_runs(num_days=365)

    print(f"Generated {len(df)} rows.")
    print(df.head())

    print("Loading synthetic runs into PostgreSQL...")
    load_runs_to_postgres(df)

    print("Done loading synthetic pipeline runs.")


if __name__ == "__main__":
    main()

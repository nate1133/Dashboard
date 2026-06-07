from pathlib import Path
import os

import joblib
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
MODEL_PATH = PROJECT_ROOT / "models" / "data_quality_issue_model.pkl"

load_dotenv(ENV_PATH)

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


FEATURE_COLS = [
    "pipeline_name",
    "source_system",
    "status",
    "rows_loaded",
    "expected_rows",
    "row_count_difference",
    "row_count_pct_difference",
    "latest_data_lag_days",
    "missing_entity_count",
    "error_count",
    "warning_count",
    "duration_seconds",
    "data_quality_score",
    "day_of_week",
    "run_hour",
]


def load_recent_runs(limit: int = 100) -> pd.DataFrame:
    query = f"""
        SELECT
            run_id,
            pipeline_name,
            source_system,
            status,
            rows_loaded,
            expected_rows,
            row_count_difference,
            row_count_pct_difference,
            latest_data_lag_days,
            missing_entity_count,
            error_count,
            warning_count,
            duration_seconds,
            data_quality_score,
            EXTRACT(DOW FROM run_start_time) AS day_of_week,
            EXTRACT(HOUR FROM run_start_time) AS run_hour
        FROM pipeline_monitoring.pipeline_runs
        ORDER BY run_start_time DESC
        LIMIT {limit};
    """

    return pd.read_sql(query, engine)


def assign_risk_factors(row: pd.Series) -> list[str]:
    risk_factors = []

    if row.get("error_count", 0) and row["error_count"] > 0:
        risk_factors.append("errors_present")

    if row.get("latest_data_lag_days", 0) and row["latest_data_lag_days"] >= 3:
        risk_factors.append("stale_data")

    if row.get("missing_entity_count", 0) and row["missing_entity_count"] > 0:
        risk_factors.append("missing_entities")

    if row.get("row_count_pct_difference") is not None and row["row_count_pct_difference"] < -25:
        risk_factors.append("row_count_drop")

    if row.get("warning_count", 0) and row["warning_count"] >= 5:
        risk_factors.append("warning_spike")

    if row.get("duration_seconds") is not None and row["duration_seconds"] > 180:
        risk_factors.append("slow_load")

    if row.get("data_quality_score") is not None and row["data_quality_score"] < 70:
        risk_factors.append("low_quality_score")

    while len(risk_factors) < 3:
        risk_factors.append(None)

    return risk_factors[:3]


def clear_existing_predictions(run_ids: list[int]) -> None:
    if not run_ids:
        return

    delete_sql = text("""
        DELETE FROM pipeline_monitoring.pipeline_predictions
        WHERE run_id = ANY(:run_ids);
    """)

    with engine.begin() as conn:
        conn.execute(delete_sql, {"run_ids": run_ids})


def save_predictions(predictions_df: pd.DataFrame) -> None:
    insert_sql = text("""
        INSERT INTO pipeline_monitoring.pipeline_predictions
        (
            run_id,
            model_name,
            model_version,
            predicted_issue_flag,
            issue_probability,
            top_risk_factor_1,
            top_risk_factor_2,
            top_risk_factor_3
        )
        VALUES
        (
            :run_id,
            :model_name,
            :model_version,
            :predicted_issue_flag,
            :issue_probability,
            :top_risk_factor_1,
            :top_risk_factor_2,
            :top_risk_factor_3
        );
    """)

    with engine.begin() as conn:
        for _, row in predictions_df.iterrows():
            conn.execute(insert_sql, row.to_dict())


def main() -> None:
    print("Loading model...")
    model = joblib.load(MODEL_PATH)

    print("Loading recent pipeline runs...")
    runs_df = load_recent_runs(limit=200)

    if runs_df.empty:
        print("No runs found to score.")
        return

    X = runs_df[FEATURE_COLS]

    print("Scoring pipeline runs...")
    probabilities = model.predict_proba(X)[:, 1]
    predictions = model.predict(X)

    output_rows = []

    for idx, row in runs_df.iterrows():
        risk_factors = assign_risk_factors(row)

        output_rows.append(
            {
                "run_id": int(row["run_id"]),
                "model_name": "RandomForestClassifier",
                "model_version": "v1.0",
                "predicted_issue_flag": int(predictions[idx]),
                "issue_probability": float(probabilities[idx]),
                "top_risk_factor_1": risk_factors[0],
                "top_risk_factor_2": risk_factors[1],
                "top_risk_factor_3": risk_factors[2],
            }
        )

    predictions_df = pd.DataFrame(output_rows)

    print("Clearing old predictions for same runs...")
    clear_existing_predictions(predictions_df["run_id"].tolist())

    print("Saving predictions to PostgreSQL...")
    save_predictions(predictions_df)

    print(f"Saved {len(predictions_df)} predictions.")
    print(predictions_df.head())


if __name__ == "__main__":
    main()

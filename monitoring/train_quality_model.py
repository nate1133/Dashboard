from pathlib import Path
import sys

import joblib
import pandas as pd
from sqlalchemy import text

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODEL_DIR / "data_quality_issue_model.pkl"

sys.path.insert(0, str(PROJECT_ROOT))

from app.db import create_db_engine

engine = create_db_engine()


def load_training_data() -> pd.DataFrame:
    query = """
        SELECT
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
            EXTRACT(HOUR FROM run_start_time) AS run_hour,
            issue_flag
        FROM pipeline_monitoring.pipeline_runs
        WHERE issue_flag IS NOT NULL;
    """

    return pd.read_sql(query, engine)


def train_model(df: pd.DataFrame):
    target = "issue_flag"

    feature_cols = [
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

    X = df[feature_cols]
    y = df[target]

    class_counts = y.value_counts()
    if len(class_counts) < 2:
        raise ValueError(
            "Training data must contain both healthy and issue runs before a classifier can be trained."
        )

    if class_counts.min() < 2:
        raise ValueError(
            "Training data needs at least two rows in each issue_flag class for stratified splitting."
        )

    categorical_features = [
        "pipeline_name",
        "source_system",
        "status",
    ]

    numeric_features = [
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

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=5,
        random_state=42,
        class_weight="balanced",
    )

    clf = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model),
        ]
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision_score": precision_score(y_test, y_pred, zero_division=0),
        "recall_score": recall_score(y_test, y_pred, zero_division=0),
        "f1_score": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_test, y_prob),
        "training_rows": len(X_train),
        "test_rows": len(X_test),
    }

    print("\nModel Metrics")
    print("=" * 60)
    for key, value in metrics.items():
        print(f"{key}: {value}")

    print("\nClassification Report")
    print("=" * 60)
    print(classification_report(y_test, y_pred, zero_division=0))

    print("\nConfusion Matrix")
    print("=" * 60)
    print(confusion_matrix(y_test, y_pred))

    return clf, metrics


def save_model(model) -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\nSaved model to: {MODEL_PATH}")


def save_metrics(metrics: dict) -> None:
    insert_sql = text("""
        INSERT INTO pipeline_monitoring.model_metrics
        (
            model_name,
            model_version,
            accuracy,
            precision_score,
            recall_score,
            f1_score,
            roc_auc,
            training_rows,
            test_rows,
            notes
        )
        VALUES
        (
            :model_name,
            :model_version,
            :accuracy,
            :precision_score,
            :recall_score,
            :f1_score,
            :roc_auc,
            :training_rows,
            :test_rows,
            :notes
        );
    """)

    payload = {
        "model_name": "RandomForestClassifier",
        "model_version": "v1.0",
        "accuracy": metrics["accuracy"],
        "precision_score": metrics["precision_score"],
        "recall_score": metrics["recall_score"],
        "f1_score": metrics["f1_score"],
        "roc_auc": metrics["roc_auc"],
        "training_rows": metrics["training_rows"],
        "test_rows": metrics["test_rows"],
        "notes": "Initial model trained on synthetic pipeline monitoring data.",
    }

    with engine.begin() as conn:
        conn.execute(insert_sql, payload)

    print("Saved model metrics to PostgreSQL.")


def main() -> None:
    print("Loading training data...")
    df = load_training_data()

    print(f"Loaded {len(df)} rows.")

    if df.empty:
        raise ValueError("No training data found.")

    print(df["issue_flag"].value_counts())

    model, metrics = train_model(df)
    save_model(model)
    save_metrics(metrics)


if __name__ == "__main__":
    main()

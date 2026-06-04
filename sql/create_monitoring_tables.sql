-- ============================================================
-- Data Quality Monitoring Tables
-- Project: Finance/Economics Pipeline
-- Schema: pipeline_monitoring
-- ============================================================

CREATE SCHEMA IF NOT EXISTS pipeline_monitoring;

-- ------------------------------------------------------------
-- Table: pipeline_runs
-- One row per pipeline/script run.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pipeline_monitoring.pipeline_runs (
    run_id SERIAL PRIMARY KEY,

    pipeline_name TEXT NOT NULL,
    source_system TEXT,
    run_start_time TIMESTAMP NOT NULL,
    run_end_time TIMESTAMP,
    run_date DATE GENERATED ALWAYS AS (run_start_time::date) STORED,

    status TEXT NOT NULL,
    issue_flag INTEGER NOT NULL DEFAULT 0,
    issue_type TEXT,

    rows_loaded INTEGER DEFAULT 0,
    expected_rows INTEGER,
    row_count_difference INTEGER,
    row_count_pct_difference NUMERIC(10,4),

    latest_data_date DATE,
    expected_latest_date DATE,
    latest_data_lag_days INTEGER,

    missing_entity_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,

    duration_seconds NUMERIC(12,2),

    data_quality_score NUMERIC(6,2),
    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Table: pipeline_predictions
-- Stores model predictions for pipeline run issue risk.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pipeline_monitoring.pipeline_predictions (
    prediction_id SERIAL PRIMARY KEY,

    run_id INTEGER REFERENCES pipeline_monitoring.pipeline_runs(run_id),
    model_name TEXT NOT NULL,
    model_version TEXT,
    prediction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    predicted_issue_flag INTEGER NOT NULL,
    issue_probability NUMERIC(8,6),

    top_risk_factor_1 TEXT,
    top_risk_factor_2 TEXT,
    top_risk_factor_3 TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Table: model_metrics
-- Stores model performance results.
-- ------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pipeline_monitoring.model_metrics (
    metric_id SERIAL PRIMARY KEY,

    model_name TEXT NOT NULL,
    model_version TEXT,
    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    accuracy NUMERIC(8,6),
    precision_score NUMERIC(8,6),
    recall_score NUMERIC(8,6),
    f1_score NUMERIC(8,6),
    roc_auc NUMERIC(8,6),

    training_rows INTEGER,
    test_rows INTEGER,

    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

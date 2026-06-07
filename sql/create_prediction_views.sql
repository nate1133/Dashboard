-- ============================================================
-- Data Quality Prediction Views
-- Schema: pipeline_monitoring
-- ============================================================

DROP VIEW IF EXISTS pipeline_monitoring.pipeline_prediction_summary CASCADE;

CREATE VIEW pipeline_monitoring.pipeline_prediction_summary AS
SELECT
    r.run_id,
    r.pipeline_name,
    r.source_system,
    r.run_start_time,
    r.status,
    r.issue_flag AS actual_issue_flag,
    r.issue_type,
    r.rows_loaded,
    r.expected_rows,
    r.row_count_pct_difference,
    r.latest_data_lag_days,
    r.missing_entity_count,
    r.error_count,
    r.warning_count,
    r.duration_seconds,
    r.data_quality_score,
    p.model_name,
    p.model_version,
    p.prediction_time,
    p.predicted_issue_flag,
    ROUND(p.issue_probability * 100, 2) AS issue_probability_pct,
    p.top_risk_factor_1,
    p.top_risk_factor_2,
    p.top_risk_factor_3,
    r.notes
FROM pipeline_monitoring.pipeline_runs r
LEFT JOIN pipeline_monitoring.pipeline_predictions p
    ON r.run_id = p.run_id
ORDER BY r.run_start_time DESC;


DROP VIEW IF EXISTS pipeline_monitoring.high_risk_pipeline_runs CASCADE;

CREATE VIEW pipeline_monitoring.high_risk_pipeline_runs AS
SELECT *
FROM pipeline_monitoring.pipeline_prediction_summary
WHERE issue_probability_pct >= 50
ORDER BY issue_probability_pct DESC, run_start_time DESC;


DROP VIEW IF EXISTS pipeline_monitoring.model_performance_latest CASCADE;

CREATE VIEW pipeline_monitoring.model_performance_latest AS
SELECT
    model_name,
    model_version,
    training_date,
    accuracy,
    precision_score,
    recall_score,
    f1_score,
    roc_auc,
    training_rows,
    test_rows,
    notes
FROM pipeline_monitoring.model_metrics
ORDER BY training_date DESC
LIMIT 1;

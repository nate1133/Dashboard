-- ============================================================
-- Data Quality Monitoring Views
-- Schema: pipeline_monitoring
-- ============================================================

DROP VIEW IF EXISTS pipeline_monitoring.pipeline_health_summary CASCADE;

CREATE VIEW pipeline_monitoring.pipeline_health_summary AS
SELECT
    pipeline_name,
    source_system,
    COUNT(*) AS total_runs,
    SUM(issue_flag) AS issue_runs,
    ROUND(AVG(issue_flag) * 100, 2) AS issue_rate_pct,
    ROUND(AVG(data_quality_score), 2) AS avg_quality_score,
    ROUND(AVG(duration_seconds), 2) AS avg_duration_seconds,
    MAX(run_start_time) AS latest_run_time
FROM pipeline_monitoring.pipeline_runs
GROUP BY pipeline_name, source_system;


DROP VIEW IF EXISTS pipeline_monitoring.recent_pipeline_runs CASCADE;

CREATE VIEW pipeline_monitoring.recent_pipeline_runs AS
SELECT
    run_id,
    pipeline_name,
    source_system,
    run_start_time,
    run_end_time,
    status,
    issue_flag,
    issue_type,
    rows_loaded,
    expected_rows,
    row_count_pct_difference,
    latest_data_lag_days,
    missing_entity_count,
    error_count,
    warning_count,
    duration_seconds,
    data_quality_score,
    notes
FROM pipeline_monitoring.pipeline_runs
ORDER BY run_start_time DESC;


DROP VIEW IF EXISTS pipeline_monitoring.issue_type_summary CASCADE;

CREATE VIEW pipeline_monitoring.issue_type_summary AS
SELECT
    issue_type,
    COUNT(*) AS issue_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_issues
FROM pipeline_monitoring.pipeline_runs
WHERE issue_flag = 1
GROUP BY issue_type
ORDER BY issue_count DESC;


DROP VIEW IF EXISTS pipeline_monitoring.daily_issue_trend CASCADE;

CREATE VIEW pipeline_monitoring.daily_issue_trend AS
SELECT
    run_date,
    COUNT(*) AS total_runs,
    SUM(issue_flag) AS issue_runs,
    ROUND(AVG(issue_flag) * 100, 2) AS issue_rate_pct,
    ROUND(AVG(data_quality_score), 2) AS avg_quality_score
FROM pipeline_monitoring.pipeline_runs
GROUP BY run_date
ORDER BY run_date;

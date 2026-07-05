from __future__ import annotations

from datetime import datetime

from trading_platform.src.database.db import encode_details, get_connection, initialize_database


def write_audit_log(event_type: str, message: str, details: dict | None = None) -> None:
    initialize_database()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (timestamp, event_type, message, details)
            VALUES (?, ?, ?, ?);
            """,
            (datetime.utcnow().isoformat(), event_type, message, encode_details(details)),
        )


def write_strategy_signal(result) -> None:
    initialize_database()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO strategy_signals
                (timestamp, ticker, strategy_name, signal, score, passed_rules, failed_rules, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                datetime.utcnow().isoformat(),
                result.ticker,
                result.strategy_name,
                result.signal,
                result.score,
                encode_details(result.passed_rules),
                encode_details(result.failed_rules),
                result.explanation,
            ),
        )

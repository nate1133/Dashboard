from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from trading_platform.src.utils.config import DATABASE_DIR, DATABASE_PATH


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS account_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                cash REAL NOT NULL,
                starting_cash REAL NOT NULL,
                emergency_stop INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                order_type TEXT NOT NULL,
                strategy_name TEXT,
                status TEXT NOT NULL,
                reason TEXT
            );

            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE,
                quantity INTEGER NOT NULL,
                average_price REAL NOT NULL,
                current_price REAL NOT NULL,
                unrealized_pl REAL NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS strategy_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                ticker TEXT NOT NULL,
                strategy_name TEXT NOT NULL,
                signal TEXT NOT NULL,
                score INTEGER NOT NULL,
                passed_rules TEXT NOT NULL,
                failed_rules TEXT NOT NULL,
                explanation TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT
            );
            """
        )


def ensure_account(starting_cash: float) -> None:
    initialize_database()
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM account_state WHERE id = 1").fetchone()
        if row is None:
            conn.execute(
                """
                INSERT INTO account_state (id, cash, starting_cash, emergency_stop, updated_at)
                VALUES (1, ?, ?, 0, ?);
                """,
                (starting_cash, starting_cash, datetime.utcnow().isoformat()),
            )


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def encode_details(details: dict | list | None) -> str | None:
    if details is None:
        return None
    return json.dumps(details, default=str)

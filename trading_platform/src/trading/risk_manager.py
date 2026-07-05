from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from trading_platform.src.database.db import get_connection
from trading_platform.src.utils.config import (
    DEFAULT_WATCHLIST,
    MAX_DAILY_LOSS_PCT,
    MAX_POSITION_PCT,
    MAX_TRADES_PER_DAY,
)


@dataclass
class RiskDecision:
    approved: bool
    passed: list[str]
    failed: list[str]


class RiskManager:
    def __init__(
        self,
        allowed_tickers: list[str] | None = None,
        max_position_pct: float = MAX_POSITION_PCT,
        max_daily_loss_pct: float = MAX_DAILY_LOSS_PCT,
        max_trades_per_day: int = MAX_TRADES_PER_DAY,
    ) -> None:
        self.allowed_tickers = {ticker.upper() for ticker in (allowed_tickers or DEFAULT_WATCHLIST)}
        self.max_position_pct = max_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_trades_per_day = max_trades_per_day

    def evaluate_order(
        self,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
        account: dict,
        existing_position_qty: int,
    ) -> RiskDecision:
        passed = []
        failed = []
        symbol = ticker.upper()
        side = side.upper()
        notional = quantity * price
        account_value = account["account_value"]

        self._check(symbol in self.allowed_tickers, "Ticker is on the allowed list", passed, failed)
        self._check(not account["emergency_stop"], "Emergency stop is off", passed, failed)
        self._check(side in {"BUY", "SELL"}, "Order side is supported", passed, failed)
        self._check(quantity > 0, "Quantity is positive", passed, failed)
        self._check(side != "SHORT", "Short selling is disabled", passed, failed)

        if side == "BUY":
            self._check(account["cash"] >= notional, "Enough cash is available", passed, failed)
            self._check(
                notional <= account_value * self.max_position_pct,
                f"Position value is within {self.max_position_pct:.0%} account limit",
                passed,
                failed,
            )
        elif side == "SELL":
            self._check(existing_position_qty >= quantity, "Sell quantity does not exceed open position", passed, failed)

        self._check(
            self._trades_today() < self.max_trades_per_day,
            f"Daily trade count is below {self.max_trades_per_day}",
            passed,
            failed,
        )
        self._check(
            account["realized_pl_today"] >= -(account_value * self.max_daily_loss_pct),
            f"Daily realized loss is within {self.max_daily_loss_pct:.0%} limit",
            passed,
            failed,
        )

        return RiskDecision(approved=not failed, passed=passed, failed=failed)

    @staticmethod
    def _check(condition: bool, label: str, passed: list[str], failed: list[str]) -> None:
        if condition:
            passed.append(label)
        else:
            failed.append(label)

    @staticmethod
    def _trades_today() -> int:
        today_prefix = date.today().isoformat()
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM trades
                WHERE status = 'FILLED'
                    AND substr(timestamp, 1, 10) = ?;
                """,
                (today_prefix,),
            ).fetchone()
        return int(row["count"])

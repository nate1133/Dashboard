from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from trading_platform.src.database.db import (
    ensure_account,
    get_connection,
    initialize_database,
    rows_to_dicts,
)
from trading_platform.src.reporting.trade_journal import write_audit_log
from trading_platform.src.trading.risk_manager import RiskManager
from trading_platform.src.utils.config import STARTING_CASH


class SimulatedBroker:
    def __init__(self, starting_cash: float = STARTING_CASH, allowed_tickers: list[str] | None = None) -> None:
        ensure_account(starting_cash)
        self.risk_manager = RiskManager(allowed_tickers=allowed_tickers)

    def get_account(self) -> dict:
        initialize_database()
        with get_connection() as conn:
            account = conn.execute("SELECT * FROM account_state WHERE id = 1").fetchone()
            positions = rows_to_dicts(conn.execute("SELECT * FROM positions").fetchall())

        cash = float(account["cash"])
        position_value = sum(float(position["current_price"]) * int(position["quantity"]) for position in positions)
        realized_pl_today = self._realized_pl_today()

        return {
            "cash": cash,
            "starting_cash": float(account["starting_cash"]),
            "position_value": position_value,
            "account_value": cash + position_value,
            "realized_pl_today": realized_pl_today,
            "emergency_stop": bool(account["emergency_stop"]),
        }

    def get_positions(self) -> pd.DataFrame:
        with get_connection() as conn:
            rows = rows_to_dicts(conn.execute("SELECT * FROM positions ORDER BY ticker").fetchall())
        return pd.DataFrame(rows)

    def get_orders(self) -> pd.DataFrame:
        with get_connection() as conn:
            rows = rows_to_dicts(conn.execute("SELECT * FROM trades ORDER BY timestamp DESC").fetchall())
        return pd.DataFrame(rows)

    def set_emergency_stop(self, enabled: bool) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE account_state SET emergency_stop = ?, updated_at = ? WHERE id = 1",
                (1 if enabled else 0, datetime.utcnow().isoformat()),
            )

        write_audit_log(
            "EMERGENCY_STOP",
            "Emergency stop changed.",
            {"enabled": enabled},
        )

    def submit_order(
        self,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
        strategy_name: str = "Manual",
    ) -> dict:
        symbol = ticker.upper().strip()
        side = side.upper().strip()
        now = datetime.utcnow().isoformat()
        account = self.get_account()
        position = self._get_position(symbol)
        existing_quantity = int(position["quantity"]) if position else 0

        decision = self.risk_manager.evaluate_order(
            ticker=symbol,
            side=side,
            quantity=quantity,
            price=price,
            account=account,
            existing_position_qty=existing_quantity,
        )

        status = "FILLED" if decision.approved else "REJECTED"
        reason = "Risk checks passed." if decision.approved else "; ".join(decision.failed)

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO trades
                    (timestamp, ticker, side, quantity, price, order_type, strategy_name, status, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (now, symbol, side, quantity, price, "MARKET", strategy_name, status, reason),
            )

            if decision.approved:
                if side == "BUY":
                    self._apply_buy(conn, symbol, quantity, price)
                elif side == "SELL":
                    self._apply_sell(conn, symbol, quantity, price)

        write_audit_log(
            "ORDER_DECISION",
            f"{status}: {side} {quantity} {symbol} at {price:.2f}",
            {
                "ticker": symbol,
                "strategy": strategy_name,
                "side": side,
                "price": price,
                "quantity": quantity,
                "risk_checks_passed": decision.passed,
                "risk_checks_failed": decision.failed,
                "final_decision": status,
            },
        )

        return {
            "status": status,
            "reason": reason,
            "passed": decision.passed,
            "failed": decision.failed,
        }

    def update_position_prices(self, price_map: dict[str, float]) -> None:
        with get_connection() as conn:
            for ticker, price in price_map.items():
                row = conn.execute("SELECT * FROM positions WHERE ticker = ?", (ticker,)).fetchone()
                if not row:
                    continue

                unrealized_pl = (price - float(row["average_price"])) * int(row["quantity"])
                conn.execute(
                    """
                    UPDATE positions
                    SET current_price = ?, unrealized_pl = ?, updated_at = ?
                    WHERE ticker = ?;
                    """,
                    (price, unrealized_pl, datetime.utcnow().isoformat(), ticker),
                )

    @staticmethod
    def _apply_buy(conn, ticker: str, quantity: int, price: float) -> None:
        position = conn.execute("SELECT * FROM positions WHERE ticker = ?", (ticker,)).fetchone()
        cash_delta = quantity * price

        conn.execute(
            "UPDATE account_state SET cash = cash - ?, updated_at = ? WHERE id = 1",
            (cash_delta, datetime.utcnow().isoformat()),
        )

        if position:
            old_quantity = int(position["quantity"])
            new_quantity = old_quantity + quantity
            avg_price = ((old_quantity * float(position["average_price"])) + cash_delta) / new_quantity
            unrealized_pl = (price - avg_price) * new_quantity
            conn.execute(
                """
                UPDATE positions
                SET quantity = ?, average_price = ?, current_price = ?, unrealized_pl = ?, updated_at = ?
                WHERE ticker = ?;
                """,
                (new_quantity, avg_price, price, unrealized_pl, datetime.utcnow().isoformat(), ticker),
            )
        else:
            conn.execute(
                """
                INSERT INTO positions (ticker, quantity, average_price, current_price, unrealized_pl, updated_at)
                VALUES (?, ?, ?, ?, 0, ?);
                """,
                (ticker, quantity, price, price, datetime.utcnow().isoformat()),
            )

    @staticmethod
    def _apply_sell(conn, ticker: str, quantity: int, price: float) -> None:
        position = conn.execute("SELECT * FROM positions WHERE ticker = ?", (ticker,)).fetchone()
        if not position:
            return

        new_quantity = int(position["quantity"]) - quantity
        conn.execute(
            "UPDATE account_state SET cash = cash + ?, updated_at = ? WHERE id = 1",
            (quantity * price, datetime.utcnow().isoformat()),
        )

        if new_quantity <= 0:
            conn.execute("DELETE FROM positions WHERE ticker = ?", (ticker,))
        else:
            average_price = float(position["average_price"])
            unrealized_pl = (price - average_price) * new_quantity
            conn.execute(
                """
                UPDATE positions
                SET quantity = ?, current_price = ?, unrealized_pl = ?, updated_at = ?
                WHERE ticker = ?;
                """,
                (new_quantity, price, unrealized_pl, datetime.utcnow().isoformat(), ticker),
            )

    @staticmethod
    def _get_position(ticker: str):
        with get_connection() as conn:
            return conn.execute("SELECT * FROM positions WHERE ticker = ?", (ticker,)).fetchone()

    @staticmethod
    def _realized_pl_today() -> float:
        today_prefix = date.today().isoformat()
        with get_connection() as conn:
            buys = rows_to_dicts(
                conn.execute(
                    """
                    SELECT ticker, quantity, price
                    FROM trades
                    WHERE status = 'FILLED' AND side = 'BUY' AND substr(timestamp, 1, 10) = ?;
                    """,
                    (today_prefix,),
                ).fetchall()
            )
            sells = rows_to_dicts(
                conn.execute(
                    """
                    SELECT ticker, quantity, price
                    FROM trades
                    WHERE status = 'FILLED' AND side = 'SELL' AND substr(timestamp, 1, 10) = ?;
                    """,
                    (today_prefix,),
                ).fetchall()
            )

        avg_buy_price = {}
        for buy in buys:
            ticker = buy["ticker"]
            avg_buy_price.setdefault(ticker, []).append((buy["quantity"], buy["price"]))

        realized = 0.0
        for sell in sells:
            lots = avg_buy_price.get(sell["ticker"], [])
            if not lots:
                continue

            total_qty = sum(quantity for quantity, _ in lots)
            total_cost = sum(quantity * price for quantity, price in lots)
            average_cost = total_cost / total_qty if total_qty else sell["price"]
            realized += (sell["price"] - average_cost) * sell["quantity"]

        return realized

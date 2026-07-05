from dataclasses import dataclass

import pandas as pd

from trading_platform.src.strategies.bullish_momentum import BullishMomentumStrategy


@dataclass
class BacktestResult:
    summary: dict
    equity_curve: pd.DataFrame
    trades: pd.DataFrame


class Backtester:
    def __init__(
        self,
        starting_balance: float = 100_000.0,
        allocation_pct: float = 0.95,
    ) -> None:
        self.starting_balance = starting_balance
        self.allocation_pct = allocation_pct
        self.strategy = BullishMomentumStrategy()

    def run(self, ticker: str, history: pd.DataFrame) -> BacktestResult:
        if history.empty or len(history) < 220:
            return BacktestResult(
                summary={"error": "At least 220 trading days are required for this backtest."},
                equity_curve=pd.DataFrame(),
                trades=pd.DataFrame(),
            )

        cash = self.starting_balance
        shares = 0
        entry_price = 0.0
        rows = []
        trade_rows = []
        realized_returns = []

        for index in range(200, len(history)):
            window = history.iloc[: index + 1]
            latest = window.iloc[-1]
            price = float(latest["close"])
            result = self.strategy.evaluate(ticker, window)

            buy_signal = result.signal == "BUY CANDIDATE"
            exit_signal = result.score < 60

            if shares == 0 and buy_signal:
                order_value = cash * self.allocation_pct
                quantity = int(order_value // price)

                if quantity > 0:
                    shares = quantity
                    entry_price = price
                    cash -= quantity * price
                    trade_rows.append(
                        {
                            "date": latest["date"],
                            "side": "BUY",
                            "quantity": quantity,
                            "price": round(price, 2),
                            "signal_score": result.score,
                        }
                    )

            elif shares > 0 and exit_signal:
                cash += shares * price
                realized_returns.append((price / entry_price) - 1)
                trade_rows.append(
                    {
                        "date": latest["date"],
                        "side": "SELL",
                        "quantity": shares,
                        "price": round(price, 2),
                        "signal_score": result.score,
                    }
                )
                shares = 0
                entry_price = 0.0

            equity = cash + shares * price
            rows.append({"date": latest["date"], "equity": equity, "cash": cash, "shares": shares})

        if shares > 0:
            latest = history.iloc[-1]
            price = float(latest["close"])
            cash += shares * price
            realized_returns.append((price / entry_price) - 1)
            trade_rows.append(
                {
                    "date": latest["date"],
                    "side": "SELL",
                    "quantity": shares,
                    "price": round(price, 2),
                    "signal_score": "final close",
                }
            )
            shares = 0

        equity_curve = pd.DataFrame(rows)
        trades = pd.DataFrame(trade_rows)

        if equity_curve.empty:
            ending_balance = self.starting_balance
            max_drawdown = 0
        else:
            ending_balance = float(equity_curve["equity"].iloc[-1])
            running_max = equity_curve["equity"].cummax()
            drawdown = (equity_curve["equity"] / running_max) - 1
            max_drawdown = float(drawdown.min() * 100)

        first_price = float(history["close"].iloc[200])
        last_price = float(history["close"].iloc[-1])
        buy_hold_return = ((last_price / first_price) - 1) * 100
        total_return = ((ending_balance / self.starting_balance) - 1) * 100
        winning_returns = [value for value in realized_returns if value > 0]
        losing_returns = [value for value in realized_returns if value <= 0]

        summary = {
            "starting_balance": round(self.starting_balance, 2),
            "ending_balance": round(ending_balance, 2),
            "total_return_pct": round(total_return, 2),
            "buy_hold_return_pct": round(buy_hold_return, 2),
            "number_of_trades": int(len(trades)),
            "win_rate_pct": round(len(winning_returns) / len(realized_returns) * 100, 2)
            if realized_returns
            else 0,
            "average_gain_pct": round(sum(winning_returns) / len(winning_returns) * 100, 2)
            if winning_returns
            else 0,
            "average_loss_pct": round(sum(losing_returns) / len(losing_returns) * 100, 2)
            if losing_returns
            else 0,
            "max_drawdown_pct": round(max_drawdown, 2),
        }

        return BacktestResult(summary=summary, equity_curve=equity_curve, trades=trades)

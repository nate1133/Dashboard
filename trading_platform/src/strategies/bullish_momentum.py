from dataclasses import dataclass

import pandas as pd


@dataclass
class StrategyResult:
    ticker: str
    strategy_name: str
    signal: str
    score: int
    passed_rules: list[str]
    failed_rules: list[str]
    explanation: str


class BullishMomentumStrategy:
    name = "Bullish Momentum"

    def evaluate(self, ticker: str, history: pd.DataFrame) -> StrategyResult:
        if history.empty or len(history) < 200:
            return StrategyResult(
                ticker=ticker.upper(),
                strategy_name=self.name,
                signal="AVOID",
                score=0,
                passed_rules=[],
                failed_rules=["At least 200 trading days of history are required."],
                explanation="The strategy needs enough history to calculate the 200-day moving average.",
            )

        latest = history.iloc[-1]
        checks = [
            (
                "Close is above the 50-day moving average",
                latest["close"] > latest["sma_50"],
            ),
            (
                "50-day moving average is above the 200-day moving average",
                latest["sma_50"] > latest["sma_200"],
            ),
            (
                "RSI is between 45 and 70",
                45 <= latest["rsi_14"] <= 70,
            ),
            (
                "MACD line is above the signal line",
                latest["macd"] > latest["macd_signal"],
            ),
            (
                "Volume is above the 20-day average",
                latest["volume"] > latest["volume_sma_20"],
            ),
        ]

        passed = [label for label, did_pass in checks if bool(did_pass)]
        failed = [label for label, did_pass in checks if not bool(did_pass)]
        score = int(round(len(passed) / len(checks) * 100))
        signal = self._signal_from_score(score)

        explanation = (
            f"{ticker.upper()} passed {len(passed)} of {len(checks)} bullish momentum rules. "
            f"The resulting rule score is {score}, which maps to {signal}."
        )

        return StrategyResult(
            ticker=ticker.upper(),
            strategy_name=self.name,
            signal=signal,
            score=score,
            passed_rules=passed,
            failed_rules=failed,
            explanation=explanation,
        )

    @staticmethod
    def _signal_from_score(score: int) -> str:
        if score >= 80:
            return "BUY CANDIDATE"
        if score >= 60:
            return "WATCH"
        if score >= 40:
            return "NEUTRAL"
        return "AVOID"

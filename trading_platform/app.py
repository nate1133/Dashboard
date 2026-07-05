from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading_platform.src.backtesting.backtester import Backtester
from trading_platform.src.data.indicators import classify_market_state
from trading_platform.src.data.market_data import get_latest_snapshot, get_price_history
from trading_platform.src.database.db import get_connection, initialize_database, rows_to_dicts
from trading_platform.src.reporting.trade_journal import write_strategy_signal
from trading_platform.src.strategies.bullish_momentum import BullishMomentumStrategy
from trading_platform.src.trading.simulated_broker import SimulatedBroker
from trading_platform.src.utils.config import DEFAULT_WATCHLIST, MAJOR_INDEX_TICKERS, STARTING_CASH


st.set_page_config(
    page_title="Trading Intelligence Platform",
    page_icon="📊",
    layout="wide",
)

initialize_database()


@st.cache_data(ttl=300, show_spinner=False)
def cached_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    return get_price_history(ticker, period=period)


@st.cache_data(ttl=300, show_spinner=False)
def cached_snapshot(tickers: tuple[str, ...]) -> pd.DataFrame:
    return get_latest_snapshot(list(tickers))


def parse_watchlist(raw_value: str) -> list[str]:
    tickers = [item.strip().upper() for item in raw_value.replace("\n", ",").split(",")]
    return [ticker for ticker in tickers if ticker]


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def latest_price(ticker: str) -> float | None:
    history = cached_history(ticker, period="6mo")
    if history.empty:
        return None
    return float(history["close"].iloc[-1])


def signal_badge(signal: str) -> str:
    return {
        "BUY CANDIDATE": "BUY CANDIDATE",
        "WATCH": "WATCH",
        "NEUTRAL": "NEUTRAL",
        "AVOID": "AVOID",
    }.get(signal, signal)


if "watchlist" not in st.session_state:
    st.session_state.watchlist = DEFAULT_WATCHLIST.copy()

broker = SimulatedBroker(starting_cash=STARTING_CASH, allowed_tickers=st.session_state.watchlist)
account = broker.get_account()

st.sidebar.title("Trading Intelligence")
st.sidebar.caption("Education and paper trading only. No live orders.")
st.sidebar.metric("Paper Account", format_currency(account["account_value"]))
st.sidebar.metric("Cash", format_currency(account["cash"]))

emergency_stop = st.sidebar.toggle("Emergency stop", value=account["emergency_stop"])
if emergency_stop != account["emergency_stop"]:
    broker.set_emergency_stop(emergency_stop)
    st.rerun()

st.sidebar.divider()
watchlist_text = st.sidebar.text_area(
    "Watchlist",
    value=", ".join(st.session_state.watchlist),
    height=110,
)
st.session_state.watchlist = parse_watchlist(watchlist_text) or DEFAULT_WATCHLIST.copy()
st.sidebar.caption("Mode: Research / Paper Trading")

st.title("Trading Intelligence Platform")
st.caption("Rule-based stock research, backtesting, and simulated paper trading. Live trading is disabled.")

home_tab, research_tab, scanner_tab, backtest_tab, paper_tab, settings_tab = st.tabs(
    [
        "Home Dashboard",
        "Stock Research",
        "Strategy Scanner",
        "Backtesting",
        "Paper Trading",
        "Settings",
    ]
)


with home_tab:
    st.subheader("Market Dashboard")

    tickers = tuple(dict.fromkeys(MAJOR_INDEX_TICKERS + st.session_state.watchlist))

    try:
        snapshot = cached_snapshot(tickers)
    except Exception as error:
        st.error("Market data could not be loaded.")
        st.exception(error)
        snapshot = pd.DataFrame()

    if snapshot.empty:
        st.info("No market snapshot data is available yet.")
    else:
        index_col, watch_col = st.columns([1, 2])
        with index_col:
            st.markdown("### Major Index ETFs")
            st.dataframe(
                snapshot[snapshot["ticker"].isin(MAJOR_INDEX_TICKERS)],
                hide_index=True,
                width="stretch",
            )
        with watch_col:
            st.markdown("### Watchlist")
            st.dataframe(
                snapshot[snapshot["ticker"].isin(st.session_state.watchlist)],
                hide_index=True,
                width="stretch",
            )

        advancing = int((snapshot["daily_change_pct"] > 0).sum()) if "daily_change_pct" in snapshot else 0
        declining = int((snapshot["daily_change_pct"] < 0).sum()) if "daily_change_pct" in snapshot else 0
        avg_change = snapshot["daily_change_pct"].dropna().mean() if "daily_change_pct" in snapshot else 0
        summary = (
            f"{advancing} symbols are positive and {declining} are negative in the current snapshot. "
            f"The average daily move across the list is {avg_change:.2f}%."
        )
        st.markdown("### Recent Market Summary")
        st.write(summary)

        movers = snapshot.dropna(subset=["daily_change_pct"]).sort_values("daily_change_pct", ascending=False)
        if not movers.empty:
            mover_fig = px.bar(
                movers,
                x="ticker",
                y="daily_change_pct",
                color="daily_change_pct",
                title="Daily Change by Symbol",
                labels={"daily_change_pct": "Daily Change %", "ticker": "Ticker"},
            )
            st.plotly_chart(mover_fig, width="stretch")


with research_tab:
    st.subheader("Stock Research")
    ticker = st.text_input("Ticker symbol", value="AAPL", key="research_ticker").upper().strip()
    period = st.selectbox("History", ["6mo", "1y", "2y", "5y"], index=2)

    if ticker:
        history = cached_history(ticker, period=period)

        if history.empty:
            st.warning("No price history found for that ticker.")
        else:
            latest = history.iloc[-1]
            prior = history.iloc[-2] if len(history) > 1 else latest
            daily_return = ((latest["close"] / prior["close"]) - 1) * 100 if prior["close"] else 0

            metric_cols = st.columns(5)
            metric_cols[0].metric("Latest Price", format_currency(float(latest["close"])))
            metric_cols[1].metric("Daily Return", f"{daily_return:.2f}%")
            metric_cols[2].metric("RSI 14", f"{latest['rsi_14']:.1f}" if pd.notna(latest["rsi_14"]) else "N/A")
            metric_cols[3].metric("20D Volatility", f"{latest['volatility_20d_pct']:.2f}%" if pd.notna(latest["volatility_20d_pct"]) else "N/A")
            metric_cols[4].metric("State", classify_market_state(history))

            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=history["date"],
                open=history["open"],
                high=history["high"],
                low=history["low"],
                close=history["close"],
                name="Price",
            ))
            for column, label in [("sma_20", "SMA 20"), ("sma_50", "SMA 50"), ("sma_200", "SMA 200")]:
                if column in history:
                    fig.add_trace(go.Scatter(x=history["date"], y=history[column], mode="lines", name=label))
            fig.update_layout(title=f"{ticker} Price and Moving Averages", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, width="stretch")

            indicator_col, volume_col = st.columns(2)
            with indicator_col:
                macd_fig = go.Figure()
                macd_fig.add_trace(go.Scatter(x=history["date"], y=history["macd"], mode="lines", name="MACD"))
                macd_fig.add_trace(go.Scatter(x=history["date"], y=history["macd_signal"], mode="lines", name="Signal"))
                macd_fig.update_layout(title="MACD")
                st.plotly_chart(macd_fig, width="stretch")

            with volume_col:
                volume_fig = px.bar(history, x="date", y="volume", title="Volume Trend")
                volume_fig.add_scatter(x=history["date"], y=history["volume_sma_20"], mode="lines", name="20D Avg")
                st.plotly_chart(volume_fig, width="stretch")

            st.markdown("### 52-Week Range")
            range_cols = st.columns(2)
            range_cols[0].metric("52-Week High", format_currency(float(latest["52w_high"])))
            range_cols[1].metric("52-Week Low", format_currency(float(latest["52w_low"])))


with scanner_tab:
    st.subheader("Strategy Scanner")
    st.caption("Bullish Momentum Strategy: trend, RSI, volume, and MACD rules.")

    strategy = BullishMomentumStrategy()
    scan_rows = []

    for symbol in st.session_state.watchlist:
        history = cached_history(symbol, period="2y")
        result = strategy.evaluate(symbol, history)
        scan_rows.append(
            {
                "ticker": symbol,
                "signal": signal_badge(result.signal),
                "score": result.score,
                "passed": len(result.passed_rules),
                "failed": len(result.failed_rules),
                "explanation": result.explanation,
            }
        )
        write_strategy_signal(result)

    scan_df = pd.DataFrame(scan_rows).sort_values(["score", "ticker"], ascending=[False, True])
    st.dataframe(scan_df, hide_index=True, width="stretch")

    selected_scan_ticker = st.selectbox("Review ticker", options=scan_df["ticker"].tolist())
    selected_history = cached_history(selected_scan_ticker, period="2y")
    selected_result = strategy.evaluate(selected_scan_ticker, selected_history)

    detail_col1, detail_col2 = st.columns(2)
    with detail_col1:
        st.markdown("### Rules Passed")
        for item in selected_result.passed_rules:
            st.success(item)
    with detail_col2:
        st.markdown("### Rules Failed")
        for item in selected_result.failed_rules:
            st.warning(item)

    st.write(selected_result.explanation)


with backtest_tab:
    st.subheader("Backtesting")
    backtest_ticker = st.text_input("Ticker to backtest", value="SPY", key="backtest_ticker").upper().strip()
    starting_balance = st.number_input("Starting balance", min_value=1_000, value=100_000, step=5_000)

    if st.button("Run Backtest", type="primary"):
        history = cached_history(backtest_ticker, period="5y")
        result = Backtester(starting_balance=float(starting_balance)).run(backtest_ticker, history)

        if "error" in result.summary:
            st.warning(result.summary["error"])
        else:
            summary = result.summary
            cols = st.columns(5)
            cols[0].metric("Ending Balance", format_currency(summary["ending_balance"]))
            cols[1].metric("Total Return", f"{summary['total_return_pct']}%")
            cols[2].metric("Buy & Hold", f"{summary['buy_hold_return_pct']}%")
            cols[3].metric("Trades", summary["number_of_trades"])
            cols[4].metric("Max Drawdown", f"{summary['max_drawdown_pct']}%")

            cols2 = st.columns(3)
            cols2[0].metric("Win Rate", f"{summary['win_rate_pct']}%")
            cols2[1].metric("Avg Gain", f"{summary['average_gain_pct']}%")
            cols2[2].metric("Avg Loss", f"{summary['average_loss_pct']}%")

            equity_fig = px.line(result.equity_curve, x="date", y="equity", title="Equity Curve")
            st.plotly_chart(equity_fig, width="stretch")

            st.markdown("### Trade Log")
            st.dataframe(result.trades, hide_index=True, width="stretch")


with paper_tab:
    st.subheader("Paper Trading")
    account = broker.get_account()

    account_cols = st.columns(4)
    account_cols[0].metric("Account Value", format_currency(account["account_value"]))
    account_cols[1].metric("Cash", format_currency(account["cash"]))
    account_cols[2].metric("Position Value", format_currency(account["position_value"]))
    account_cols[3].metric("Realized P/L Today", format_currency(account["realized_pl_today"]))

    order_col, status_col = st.columns([1, 2])

    with order_col:
        st.markdown("### Simulated Market Order")
        order_ticker = st.selectbox("Ticker", options=st.session_state.watchlist)
        side = st.selectbox("Side", options=["BUY", "SELL"])
        price = latest_price(order_ticker)
        if price is None:
            st.warning("Latest price is unavailable.")
            price = 0.0
        st.metric("Estimated Market Price", format_currency(price))
        quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
        strategy_name = st.text_input("Strategy name", value="Manual")

        if st.button("Submit Paper Order", type="primary", disabled=price <= 0):
            result = broker.submit_order(
                ticker=order_ticker,
                side=side,
                quantity=int(quantity),
                price=float(price),
                strategy_name=strategy_name,
            )
            if result["status"] == "FILLED":
                st.success(result["reason"])
            else:
                st.error(result["reason"])

    with status_col:
        st.markdown("### Open Positions")
        positions = broker.get_positions()
        if positions.empty:
            st.info("No open paper positions.")
        else:
            price_updates = {}
            for symbol in positions["ticker"].tolist():
                current = latest_price(symbol)
                if current is not None:
                    price_updates[symbol] = current
            broker.update_position_prices(price_updates)
            positions = broker.get_positions()
            st.dataframe(positions, hide_index=True, width="stretch")

        st.markdown("### Trade History")
        orders = broker.get_orders()
        if orders.empty:
            st.info("No paper trades yet.")
        else:
            st.dataframe(orders, hide_index=True, width="stretch")


with settings_tab:
    st.subheader("Settings & Audit")
    st.warning("Live trading is not implemented. This app only supports research and simulated paper trades.")

    settings_cols = st.columns(3)
    settings_cols[0].metric("Max Position Size", "5%")
    settings_cols[1].metric("Max Daily Loss", "2%")
    settings_cols[2].metric("Max Trades / Day", "5")

    st.markdown("### Safety Guardrails")
    st.write(
        "Long-only stocks, no margin, no options, allowed tickers only, emergency stop, "
        "cash checks, position-size checks, and audit logs for every order decision."
    )

    st.markdown("### Recent Audit Logs")
    with get_connection() as conn:
        logs = rows_to_dicts(
            conn.execute(
                """
                SELECT timestamp, event_type, message, details
                FROM audit_logs
                ORDER BY timestamp DESC
                LIMIT 100;
                """
            ).fetchall()
        )
    if logs:
        st.dataframe(pd.DataFrame(logs), hide_index=True, width="stretch")
    else:
        st.info("No audit logs yet.")

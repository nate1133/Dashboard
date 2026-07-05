import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from db import create_db_engine


st.set_page_config(
    page_title="Finance & Economics Dashboard",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Finance & Economics Dashboard")
st.caption("Data pipeline powered by Python, PostgreSQL, Docker, and Streamlit")


@st.cache_resource(show_spinner=False)
def get_engine():
    return create_db_engine()


@st.cache_data(ttl=600, show_spinner=False)
def read_table(query: str, date_columns: tuple[str, ...] = ()) -> pd.DataFrame:
    df = pd.read_sql(query, get_engine())

    for column in date_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")

    return df


def load_query(name: str, query: str, date_columns: tuple[str, ...] = ()) -> pd.DataFrame:
    try:
        return read_table(query, date_columns)
    except SQLAlchemyError as error:
        st.warning(f"{name} could not be loaded: {error.__class__.__name__}")
        return pd.DataFrame()


def empty_frame_message(label: str) -> None:
    st.info(f"No {label} data is available yet.")


def safe_sort(df: pd.DataFrame, columns, ascending=True) -> pd.DataFrame:
    if df.empty:
        return df

    sort_columns = [columns] if isinstance(columns, str) else list(columns)
    existing_columns = [column for column in sort_columns if column in df.columns]

    if not existing_columns:
        return df

    if isinstance(ascending, list):
        ascending = ascending[: len(existing_columns)]

    return df.sort_values(existing_columns, ascending=ascending)


try:
    get_engine()
except Exception as error:
    st.error("The dashboard could not connect to PostgreSQL.")
    st.exception(error)
    st.stop()


latest_prices = load_query(
    "latest stock prices",
    """
        SELECT *
        FROM finance_econ.latest_stock_prices
        ORDER BY ticker;
    """,
    ("price_date", "loaded_at"),
)

performance = load_query(
    "performance summary",
    """
        SELECT *
        FROM finance_econ.stock_performance_summary
        ORDER BY total_return_pct DESC;
    """,
    ("first_date", "last_date"),
)

stock_prices = load_query(
    "stock prices",
    """
        SELECT
            sp.ticker,
            tm.name,
            tm.category,
            sp.price_date,
            sp.adjusted_close,
            sp.volume
        FROM finance_econ.stock_prices sp
        LEFT JOIN finance_econ.ticker_metadata tm
            ON sp.ticker = tm.ticker
        ORDER BY sp.ticker, sp.price_date;
    """,
    ("price_date",),
)

monthly_returns = load_query(
    "monthly returns",
    """
        SELECT
            ticker,
            name,
            category,
            month_start,
            monthly_return_pct
        FROM finance_econ.monthly_stock_returns
        ORDER BY month_start, ticker;
    """,
    ("month_start",),
)

risk_summary = load_query(
    "risk summary",
    """
        SELECT
            ticker,
            name,
            category,
            trading_days,
            avg_daily_return_pct,
            daily_volatility_pct,
            worst_daily_return_pct,
            best_daily_return_pct
        FROM finance_econ.stock_risk_summary
        ORDER BY daily_volatility_pct DESC;
    """,
)

latest_macro = load_query(
    "latest macro indicators",
    """
        SELECT
            indicator_code,
            indicator_name,
            observation_date,
            value,
            source,
            loaded_at
        FROM finance_econ.latest_economic_indicators
        ORDER BY indicator_code;
    """,
    ("observation_date", "loaded_at"),
)

macro_trends = load_query(
    "macro trends",
    """
        SELECT
            indicator_code,
            indicator_name,
            observation_date,
            value,
            source
        FROM finance_econ.macro_trends
        ORDER BY indicator_code, observation_date;
    """,
    ("observation_date",),
)

market_macro = load_query(
    "market vs macro",
    """
        SELECT
            month_start,
            ticker,
            monthly_return_pct,
            indicator_code,
            indicator_name,
            macro_value
        FROM finance_econ.market_macro_monthly
        ORDER BY month_start, indicator_code;
    """,
    ("month_start",),
)

pipeline_health = load_query(
    "pipeline health summary",
    """
        SELECT *
        FROM pipeline_monitoring.pipeline_health_summary
        ORDER BY issue_rate_pct DESC;
    """,
)

recent_runs = load_query(
    "recent pipeline runs",
    """
        SELECT *
        FROM pipeline_monitoring.recent_pipeline_runs
        LIMIT 100;
    """,
    ("run_start_time", "run_end_time"),
)

issue_summary = load_query(
    "issue type summary",
    """
        SELECT *
        FROM pipeline_monitoring.issue_type_summary;
    """,
)

daily_issue_trend = load_query(
    "daily issue trend",
    """
        SELECT *
        FROM pipeline_monitoring.daily_issue_trend
        ORDER BY run_date;
    """,
    ("run_date",),
)

pipeline_predictions = load_query(
    "pipeline predictions",
    """
        SELECT *
        FROM pipeline_monitoring.pipeline_prediction_summary
        ORDER BY run_start_time DESC
        LIMIT 200;
    """,
    ("run_start_time", "prediction_time"),
)

high_risk_runs = load_query(
    "high-risk pipeline runs",
    """
        SELECT *
        FROM pipeline_monitoring.high_risk_pipeline_runs
        LIMIT 50;
    """,
    ("run_start_time", "prediction_time"),
)

model_performance = load_query(
    "latest model performance",
    """
        SELECT *
        FROM pipeline_monitoring.model_performance_latest;
    """,
    ("training_date",),
)


st.sidebar.header("Filters")

categories = (
    sorted(stock_prices["category"].dropna().unique())
    if "category" in stock_prices.columns
    else []
)

selected_categories = st.sidebar.multiselect(
    "Select categories",
    options=categories,
    default=categories,
)

category_filtered = (
    stock_prices[stock_prices["category"].isin(selected_categories)]
    if selected_categories and "category" in stock_prices.columns
    else stock_prices.copy()
)

tickers = (
    sorted(category_filtered["ticker"].dropna().unique())
    if "ticker" in category_filtered.columns
    else []
)

selected_tickers = st.sidebar.multiselect(
    "Select tickers",
    options=tickers,
    default=tickers,
)

filtered_prices = (
    category_filtered[category_filtered["ticker"].isin(selected_tickers)]
    if selected_tickers and "ticker" in category_filtered.columns
    else category_filtered.iloc[0:0]
)

filtered_monthly_returns = monthly_returns.copy()
if selected_categories and "category" in filtered_monthly_returns.columns:
    filtered_monthly_returns = filtered_monthly_returns[
        filtered_monthly_returns["category"].isin(selected_categories)
    ]
if selected_tickers and "ticker" in filtered_monthly_returns.columns:
    filtered_monthly_returns = filtered_monthly_returns[
        filtered_monthly_returns["ticker"].isin(selected_tickers)
    ]

filtered_risk_summary = risk_summary.copy()
if selected_categories and "category" in filtered_risk_summary.columns:
    filtered_risk_summary = filtered_risk_summary[
        filtered_risk_summary["category"].isin(selected_categories)
    ]
if selected_tickers and "ticker" in filtered_risk_summary.columns:
    filtered_risk_summary = filtered_risk_summary[
        filtered_risk_summary["ticker"].isin(selected_tickers)
    ]

st.sidebar.divider()

macro_indicators = (
    sorted(macro_trends["indicator_name"].dropna().unique())
    if "indicator_name" in macro_trends.columns
    else []
)

selected_macro_indicators = st.sidebar.multiselect(
    "Select macro indicators",
    options=macro_indicators,
    default=macro_indicators,
)

filtered_macro_trends = (
    macro_trends[macro_trends["indicator_name"].isin(selected_macro_indicators)]
    if selected_macro_indicators and "indicator_name" in macro_trends.columns
    else macro_trends.iloc[0:0]
)

filtered_latest_macro = (
    latest_macro[latest_macro["indicator_name"].isin(selected_macro_indicators)]
    if selected_macro_indicators and "indicator_name" in latest_macro.columns
    else latest_macro.iloc[0:0]
)

market_macro_indicators = (
    sorted(market_macro["indicator_name"].dropna().unique())
    if "indicator_name" in market_macro.columns
    else []
)

selected_market_macro_indicator = None
if market_macro_indicators:
    selected_market_macro_indicator = st.sidebar.selectbox(
        "Market vs Macro indicator",
        options=market_macro_indicators,
    )

filtered_market_macro = (
    market_macro[market_macro["indicator_name"] == selected_market_macro_indicator]
    if selected_market_macro_indicator and "indicator_name" in market_macro.columns
    else market_macro.iloc[0:0]
)


overview_tab, returns_tab, risk_tab, macro_tab, market_macro_tab, pipeline_health_tab, about_tab = st.tabs(
    [
        "Overview",
        "Returns",
        "Risk & Volatility",
        "Macro Indicators",
        "Market vs Macro",
        "Pipeline Health",
        "About",
    ]
)


with overview_tab:
    st.subheader("Market Overview")

    col1, col2, col3, col4 = st.columns(4)

    latest_date = latest_prices["price_date"].max() if "price_date" in latest_prices else None
    best_row = performance.iloc[0] if not performance.empty else None
    worst_row = (
        performance.sort_values("total_return_pct", ascending=True).iloc[0]
        if "total_return_pct" in performance and not performance.empty
        else None
    )

    with col1:
        st.metric("Latest Data Date", str(latest_date.date()) if pd.notna(latest_date) else "N/A")

    with col2:
        st.metric("Tickers Tracked", len(tickers))

    with col3:
        if best_row is not None:
            st.metric("Best Performer", best_row["ticker"], f"{best_row['total_return_pct']}%")
        else:
            st.metric("Best Performer", "N/A")

    with col4:
        if worst_row is not None:
            st.metric("Worst Performer", worst_row["ticker"], f"{worst_row['total_return_pct']}%")
        else:
            st.metric("Worst Performer", "N/A")

    st.subheader("Latest Stock Prices")
    if latest_prices.empty:
        empty_frame_message("latest stock price")
    else:
        st.dataframe(latest_prices, width="stretch", hide_index=True)

    st.subheader("Performance Summary")
    if performance.empty:
        empty_frame_message("performance summary")
    else:
        st.dataframe(performance, width="stretch", hide_index=True)

    st.subheader("Adjusted Close Price Over Time")
    if filtered_prices.empty:
        empty_frame_message("filtered stock price")
    else:
        fig = px.line(
            filtered_prices,
            x="price_date",
            y="adjusted_close",
            color="ticker",
            hover_name="name",
            title="Adjusted Close by Ticker",
            labels={
                "price_date": "Date",
                "adjusted_close": "Adjusted Close",
                "ticker": "Ticker",
            },
        )
        st.plotly_chart(fig, width="stretch")


with returns_tab:
    st.subheader("Monthly Returns")

    if filtered_monthly_returns.empty:
        empty_frame_message("monthly return")
    else:
        monthly_fig = px.bar(
            filtered_monthly_returns,
            x="month_start",
            y="monthly_return_pct",
            color="ticker",
            barmode="group",
            hover_name="name",
            title="Monthly Return % by Ticker",
            labels={
                "month_start": "Month",
                "monthly_return_pct": "Monthly Return %",
                "ticker": "Ticker",
            },
        )

        st.plotly_chart(monthly_fig, width="stretch", key="monthly_returns_chart")
        st.dataframe(
            safe_sort(filtered_monthly_returns, ["month_start", "monthly_return_pct"], [False, False]),
            width="stretch",
            hide_index=True,
        )

    st.subheader("Trading Volume")
    if filtered_prices.empty:
        empty_frame_message("trading volume")
    else:
        volume_fig = px.bar(
            filtered_prices,
            x="price_date",
            y="volume",
            color="ticker",
            hover_name="name",
            title="Trading Volume by Ticker",
            labels={
                "price_date": "Date",
                "volume": "Volume",
                "ticker": "Ticker",
            },
        )

        st.plotly_chart(volume_fig, width="stretch", key="volume_chart")


with risk_tab:
    st.subheader("Risk & Volatility")

    if filtered_risk_summary.empty:
        empty_frame_message("risk summary")
    else:
        risk_col1, risk_col2 = st.columns(2)

        with risk_col1:
            vol_fig = px.bar(
                safe_sort(filtered_risk_summary, "daily_volatility_pct", False),
                x="ticker",
                y="daily_volatility_pct",
                color="category",
                hover_name="name",
                title="Daily Volatility by Ticker",
                labels={
                    "ticker": "Ticker",
                    "daily_volatility_pct": "Daily Volatility %",
                    "category": "Category",
                },
            )
            st.plotly_chart(vol_fig, width="stretch")

        with risk_col2:
            avg_return_fig = px.bar(
                safe_sort(filtered_risk_summary, "avg_daily_return_pct", False),
                x="ticker",
                y="avg_daily_return_pct",
                color="category",
                hover_name="name",
                title="Average Daily Return by Ticker",
                labels={
                    "ticker": "Ticker",
                    "avg_daily_return_pct": "Average Daily Return %",
                    "category": "Category",
                },
            )
            st.plotly_chart(avg_return_fig, width="stretch", key="volatility_chart")

        st.dataframe(
            safe_sort(filtered_risk_summary, "daily_volatility_pct", False),
            width="stretch",
            hide_index=True,
        )


with macro_tab:
    st.subheader("Macro Indicators")
    st.caption("Economic data loaded from FRED into PostgreSQL.")

    st.markdown("### Latest Macro Readings")
    if filtered_latest_macro.empty:
        empty_frame_message("latest macro indicator")
    else:
        st.dataframe(
            safe_sort(filtered_latest_macro, "indicator_code"),
            width="stretch",
            hide_index=True,
        )

    st.markdown("### Macro Trends Over Time")
    if filtered_macro_trends.empty:
        empty_frame_message("macro trend")
    else:
        macro_fig = px.line(
            filtered_macro_trends,
            x="observation_date",
            y="value",
            color="indicator_name",
            title="Economic Indicators Over Time",
            labels={
                "observation_date": "Date",
                "value": "Value",
                "indicator_name": "Indicator",
            },
        )
        st.plotly_chart(macro_fig, width="stretch", key="macro_trends_chart")

    st.markdown("### Individual Indicator Views")
    for indicator in selected_macro_indicators:
        indicator_df = filtered_macro_trends[
            filtered_macro_trends["indicator_name"] == indicator
        ]

        if indicator_df.empty:
            continue

        with st.expander(indicator):
            indicator_fig = px.line(
                indicator_df,
                x="observation_date",
                y="value",
                title=indicator,
                labels={
                    "observation_date": "Date",
                    "value": "Value",
                },
            )

            st.plotly_chart(
                indicator_fig,
                width="stretch",
                key=f"macro_chart_{indicator}",
            )

            st.dataframe(
                safe_sort(indicator_df, "observation_date", False).head(20),
                width="stretch",
                hide_index=True,
            )


with market_macro_tab:
    st.subheader("Market vs Macro")
    st.caption("Compare SPY monthly returns against selected macroeconomic indicators.")

    if filtered_market_macro.empty or not selected_market_macro_indicator:
        empty_frame_message("market and macro comparison")
    else:
        st.markdown(f"### SPY Monthly Returns vs {selected_market_macro_indicator}")

        comparison_col1, comparison_col2 = st.columns(2)

        with comparison_col1:
            spy_return_fig = px.bar(
                filtered_market_macro,
                x="month_start",
                y="monthly_return_pct",
                title="SPY Monthly Return %",
                labels={
                    "month_start": "Month",
                    "monthly_return_pct": "SPY Monthly Return %",
                },
            )

            st.plotly_chart(
                spy_return_fig,
                width="stretch",
                key="spy_monthly_return_macro_compare",
            )

        with comparison_col2:
            macro_compare_fig = px.line(
                filtered_market_macro,
                x="month_start",
                y="macro_value",
                title=selected_market_macro_indicator,
                markers=True,
                labels={
                    "month_start": "Month",
                    "macro_value": selected_market_macro_indicator,
                },
            )

            st.plotly_chart(
                macro_compare_fig,
                width="stretch",
                key="macro_compare_chart",
            )

        st.markdown("### Comparison Table")
        st.dataframe(
            safe_sort(filtered_market_macro, "month_start", False),
            width="stretch",
            hide_index=True,
        )

        st.markdown("### Simple Relationship View")
        scatter_fig = px.scatter(
            filtered_market_macro,
            x="macro_value",
            y="monthly_return_pct",
            trendline="ols",
            hover_data=["month_start"],
            title=f"SPY Monthly Return % vs {selected_market_macro_indicator}",
            labels={
                "macro_value": selected_market_macro_indicator,
                "monthly_return_pct": "SPY Monthly Return %",
            },
        )

        st.plotly_chart(scatter_fig, width="stretch", key="market_macro_scatter")


with pipeline_health_tab:
    st.subheader("Pipeline Health & Data Quality Prediction")
    st.caption(
        "Monitoring layer for pipeline run quality, issue detection, and model-based risk scoring."
    )

    if recent_runs.empty:
        empty_frame_message("recent pipeline run")
    else:
        latest_run_time = recent_runs["run_start_time"].max()
        total_recent_runs = len(recent_runs)
        issue_runs = int(recent_runs["issue_flag"].fillna(0).sum())
        avg_quality_score = round(recent_runs["data_quality_score"].mean(), 2)
        avg_quality_score = "N/A" if pd.isna(avg_quality_score) else avg_quality_score

        latest_predictions_available = (
            not pipeline_predictions.empty
            and "issue_probability_pct" in pipeline_predictions.columns
        )
        avg_issue_probability = (
            round(pipeline_predictions["issue_probability_pct"].mean(), 2)
            if latest_predictions_available
            else 0
        )

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            latest_run_value = (
                str(latest_run_time.date()) if pd.notna(latest_run_time) else "N/A"
            )
            st.metric("Latest Run", latest_run_value)

        with col2:
            st.metric("Recent Runs", total_recent_runs)

        with col3:
            st.metric("Actual Issues", issue_runs)

        with col4:
            st.metric("Avg Quality Score", avg_quality_score)

        with col5:
            st.metric("Avg Predicted Risk", f"{avg_issue_probability}%")

    st.markdown("### Pipeline Health Summary")
    if pipeline_health.empty:
        empty_frame_message("pipeline health summary")
    else:
        st.dataframe(pipeline_health, width="stretch", hide_index=True)

    st.markdown("### Issue Trends")
    if daily_issue_trend.empty:
        empty_frame_message("daily issue trend")
    else:
        trend_col1, trend_col2 = st.columns(2)

        with trend_col1:
            issue_trend_fig = px.line(
                daily_issue_trend,
                x="run_date",
                y="issue_rate_pct",
                title="Daily Issue Rate %",
                labels={
                    "run_date": "Run Date",
                    "issue_rate_pct": "Issue Rate %",
                },
            )
            st.plotly_chart(issue_trend_fig, width="stretch", key="daily_issue_rate_chart")

        with trend_col2:
            quality_trend_fig = px.line(
                daily_issue_trend,
                x="run_date",
                y="avg_quality_score",
                title="Average Data Quality Score",
                labels={
                    "run_date": "Run Date",
                    "avg_quality_score": "Avg Quality Score",
                },
            )
            st.plotly_chart(quality_trend_fig, width="stretch", key="daily_quality_score_chart")

    st.markdown("### Issue Type Breakdown")
    if issue_summary.empty:
        empty_frame_message("issue type")
    else:
        issue_type_fig = px.bar(
            issue_summary,
            x="issue_type",
            y="issue_count",
            title="Issue Count by Type",
            labels={
                "issue_type": "Issue Type",
                "issue_count": "Issue Count",
            },
        )
        st.plotly_chart(issue_type_fig, width="stretch", key="issue_type_breakdown_chart")

    st.markdown("### High-Risk Predicted Pipeline Runs")
    if high_risk_runs.empty:
        st.success("No high-risk pipeline runs found.")
    else:
        st.dataframe(high_risk_runs, width="stretch", hide_index=True)

    st.markdown("### Prediction Detail")
    if pipeline_predictions.empty:
        empty_frame_message("pipeline prediction")
    else:
        prediction_fig = px.histogram(
            pipeline_predictions,
            x="issue_probability_pct",
            nbins=20,
            title="Predicted Issue Probability Distribution",
            labels={
                "issue_probability_pct": "Predicted Issue Probability %",
            },
        )
        st.plotly_chart(prediction_fig, width="stretch", key="issue_probability_distribution")

        st.dataframe(
            safe_sort(pipeline_predictions, "issue_probability_pct", False),
            width="stretch",
            hide_index=True,
        )

    st.markdown("### Latest Model Performance")
    if model_performance.empty:
        st.warning("No model performance records found.")
    else:
        st.dataframe(model_performance, width="stretch", hide_index=True)

        model_row = model_performance.iloc[0]
        perf_col1, perf_col2, perf_col3, perf_col4, perf_col5 = st.columns(5)

        with perf_col1:
            st.metric("Accuracy", round(model_row["accuracy"], 3))

        with perf_col2:
            st.metric("Precision", round(model_row["precision_score"], 3))

        with perf_col3:
            st.metric("Recall", round(model_row["recall_score"], 3))

        with perf_col4:
            st.metric("F1 Score", round(model_row["f1_score"], 3))

        with perf_col5:
            st.metric("ROC-AUC", round(model_row["roc_auc"], 3))


with about_tab:
    st.subheader("About This Project")
    st.markdown(
        """
        This dashboard is part of a self-hosted finance and economics data pipeline.

        **Current stack:**

        - Ubuntu Server
        - Docker
        - PostgreSQL
        - Python
        - yfinance
        - SQL views
        - Streamlit
        - Plotly
        - systemd service

        **Current features:**

        - Automated stock price loading
        - Ticker metadata configuration
        - Latest price summary
        - Monthly returns
        - Risk and volatility analysis
        - Macroeconomic indicators
        - Market and macro comparison
        - Pipeline health monitoring
        """
    )

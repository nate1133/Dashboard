import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(
    page_title="Finance & Economics Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Finance & Economics Dashboard")
st.caption("Data pipeline powered by Python, PostgreSQL, Docker, and Streamlit")

# -----------------------------
# Database connection
# -----------------------------
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# -----------------------------
# Load data
# -----------------------------
@st.cache_data(ttl=600)
def load_latest_prices():
    query = """
        SELECT *
        FROM finance_econ.latest_stock_prices
        ORDER BY ticker;
    """
    return pd.read_sql(query, engine)


@st.cache_data(ttl=600)
def load_performance_summary():
    query = """
        SELECT *
        FROM finance_econ.stock_performance_summary
        ORDER BY total_return_pct DESC;
    """
    return pd.read_sql(query, engine)


@st.cache_data(ttl=600)
def load_stock_prices():
    query = """
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
    """
    df = pd.read_sql(query, engine)
    df["price_date"] = pd.to_datetime(df["price_date"])
    return df


@st.cache_data(ttl=600)
def load_monthly_returns():
    query = """
        SELECT
            ticker,
            name,
            category,
            month_start,
            monthly_return_pct
        FROM finance_econ.monthly_stock_returns
        ORDER BY month_start, ticker;
    """
    df = pd.read_sql(query, engine)
    df["month_start"] = pd.to_datetime(df["month_start"])
    return df


@st.cache_data(ttl=600)
def load_risk_summary():
    query = """
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
    """
    return pd.read_sql(query, engine)

@st.cache_data(ttl=600)
def load_latest_macro_indicators():
    query = """
        SELECT
            indicator_code,
            indicator_name,
            observation_date,
            value,
            source,
            loaded_at
        FROM finance_econ.latest_economic_indicators
        ORDER BY indicator_code;
    """
    df = pd.read_sql(query, engine)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    return df


@st.cache_data(ttl=600)
def load_macro_trends():
    query = """
        SELECT
            indicator_code,
            indicator_name,
            observation_date,
            value,
            source
        FROM finance_econ.macro_trends
        ORDER BY indicator_code, observation_date;
    """
    df = pd.read_sql(query, engine)
    df["observation_date"] = pd.to_datetime(df["observation_date"])
    return df

@st.cache_data(ttl=600)
def load_market_macro_monthly():
    query = """
        SELECT
            month_start,
            ticker,
            monthly_return_pct,
            indicator_code,
            indicator_name,
            macro_value
        FROM finance_econ.market_macro_monthly
        ORDER BY month_start, indicator_code;
    """
    df = pd.read_sql(query, engine)
    df["month_start"] = pd.to_datetime(df["month_start"])
    return df

latest_prices = load_latest_prices()
performance = load_performance_summary()
stock_prices = load_stock_prices()
monthly_returns = load_monthly_returns()
risk_summary = load_risk_summary()
latest_macro = load_latest_macro_indicators()
macro_trends = load_macro_trends()
market_macro = load_market_macro_monthly()

# -----------------------------
# Sidebar filters
# -----------------------------
st.sidebar.header("Filters")

categories = sorted(stock_prices["category"].dropna().unique())

selected_categories = st.sidebar.multiselect(
    "Select categories",
    options=categories,
    default=categories
)

category_filtered = stock_prices[
    stock_prices["category"].isin(selected_categories)
]

tickers = sorted(category_filtered["ticker"].unique())

selected_tickers = st.sidebar.multiselect(
    "Select tickers",
    options=tickers,
    default=tickers
)

filtered_prices = category_filtered[
    category_filtered["ticker"].isin(selected_tickers)
]

filtered_monthly_returns = monthly_returns[
    (monthly_returns["category"].isin(selected_categories)) &
    (monthly_returns["ticker"].isin(selected_tickers))
]

filtered_risk_summary = risk_summary[
    (risk_summary["category"].isin(selected_categories)) &
    (risk_summary["ticker"].isin(selected_tickers))
]

st.sidebar.divider()

macro_indicators = sorted(macro_trends["indicator_name"].dropna().unique())

selected_macro_indicators = st.sidebar.multiselect(
    "Select macro indicators",
    options=macro_indicators,
    default=macro_indicators
)

filtered_macro_trends = macro_trends[
    macro_trends["indicator_name"].isin(selected_macro_indicators)
]

filtered_latest_macro = latest_macro[
    latest_macro["indicator_name"].isin(selected_macro_indicators)
]

market_macro_indicators = sorted(
    market_macro["indicator_name"].dropna().unique()
)

selected_market_macro_indicator = st.sidebar.selectbox(
    "Market vs Macro indicator",
    options=market_macro_indicators
)

filtered_market_macro = market_macro[
    market_macro["indicator_name"] == selected_market_macro_indicator
]

# -----------------------------
# Dashboard tabs
# -----------------------------

overview_tab, returns_tab, risk_tab, macro_tab, market_macro_tab, about_tab = st.tabs([
    "Overview",
    "Returns",
    "Risk & Volatility",
    "Macro Indicators",
    "Market vs Macro",
    "About"
])


# -----------------------------
# KPI cards
# -----------------------------
with overview_tab:
    st.subheader("Market Overview")

    col1, col2, col3, col4 = st.columns(4)

    latest_date = latest_prices["price_date"].max()
    best_row = performance.sort_values("total_return_pct", ascending=False).iloc[0]
    worst_row = performance.sort_values("total_return_pct", ascending=True).iloc[0]

    with col1:
        st.metric("Latest Data Date", str(latest_date))

    with col2:
        st.metric("Tickers Tracked", len(tickers))

    with col3:
        st.metric(
            "Best Performer",
            best_row["ticker"],
            f"{best_row['total_return_pct']}%"
        )

    with col4:
        st.metric(
            "Worst Performer",
            worst_row["ticker"],
            f"{worst_row['total_return_pct']}%"
        )

    st.subheader("Latest Stock Prices")
    st.dataframe(
        latest_prices,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Performance Summary")
    st.dataframe(
        performance,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Adjusted Close Price Over Time")

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
            "ticker": "Ticker"
        }
    )

    st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Latest prices table
# -----------------------------
st.subheader("Latest Stock Prices")
st.dataframe(
    latest_prices,
    use_container_width=True,
    hide_index=True
)

# -----------------------------
# Performance table
# -----------------------------
st.subheader("Performance Summary")

st.dataframe(
    performance,
    use_container_width=True,
    hide_index=True
)

# -----------------------------
# Price chart
# -----------------------------
st.subheader("Adjusted Close Price Over Time")

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
        "ticker": "Ticker"
    }
)

st.plotly_chart(fig, use_container_width=True, key="adjusted_close_chart")

# -----------------------------
# Risk and volatility section
# -----------------------------
with risk_tab:
    st.subheader("Risk & Volatility")

    risk_col1, risk_col2 = st.columns(2)

    with risk_col1:
        vol_fig = px.bar(
            filtered_risk_summary.sort_values("daily_volatility_pct", ascending=False),
            x="ticker",
            y="daily_volatility_pct",
            color="category",
            hover_name="name",
            title="Daily Volatility by Ticker",
            labels={
                "ticker": "Ticker",
                "daily_volatility_pct": "Daily Volatility %",
                "category": "Category"
            }
        )
        st.plotly_chart(vol_fig, use_container_width=True)

    with risk_col2:
        avg_return_fig = px.bar(
            filtered_risk_summary.sort_values("avg_daily_return_pct", ascending=False),
            x="ticker",
            y="avg_daily_return_pct",
            color="category",
            hover_name="name",
            title="Average Daily Return by Ticker",
            labels={
                "ticker": "Ticker",
                "avg_daily_return_pct": "Average Daily Return %",
                "category": "Category"
            }
        )
        st.plotly_chart(avg_return_fig, use_container_width=True, key="volatility_chart")

    st.dataframe(
        filtered_risk_summary.sort_values("daily_volatility_pct", ascending=False),
        use_container_width=True,
        hide_index=True
    )

# -----------------------------
# Monthly returns chart
# -----------------------------
with returns_tab:
    st.subheader("Monthly Returns")

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
            "ticker": "Ticker"
        }
    )

    st.plotly_chart(monthly_fig, use_container_width=True, key="monthly_returns_chart")

    st.dataframe(
        filtered_monthly_returns.sort_values(
            ["month_start", "monthly_return_pct"],
            ascending=[False, False]
        ),
        use_container_width=True,
        hide_index=True
    )

#---------------------------
#Volume chart
#---------------------------
    st.subheader("Trading Volume")

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
            "ticker": "Ticker"
        }
    )

    st.plotly_chart(volume_fig, use_container_width=True, key="volume_chart")

#-------------------------
#Macroeconomic tab
#------------------------

with macro_tab:
    st.subheader("Macro Indicators")

    st.caption("Economic data loaded from FRED into PostgreSQL.")

    st.markdown("### Latest Macro Readings")

    st.dataframe(
        filtered_latest_macro.sort_values("indicator_code"),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Macro Trends Over Time")

    macro_fig = px.line(
        filtered_macro_trends,
        x="observation_date",
        y="value",
        color="indicator_name",
        title="Economic Indicators Over Time",
        labels={
            "observation_date": "Date",
            "value": "Value",
            "indicator_name": "Indicator"
        }
    )

    st.plotly_chart(
        macro_fig,
        use_container_width=True,
        key="macro_trends_chart"
    )

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
                    "value": "Value"
                }
            )

            st.plotly_chart(
                indicator_fig,
                use_container_width=True,
                key=f"macro_chart_{indicator}"
            )

            st.dataframe(
                indicator_df.sort_values("observation_date", ascending=False).head(20),
                use_container_width=True,
                hide_index=True
            )


with market_macro_tab:
    st.subheader("Market vs Macro")

    st.caption(
        "Compare SPY monthly returns against selected macroeconomic indicators."
    )

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
                "monthly_return_pct": "SPY Monthly Return %"
            }
        )

        st.plotly_chart(
            spy_return_fig,
            use_container_width=True,
            key="spy_monthly_return_macro_compare"
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
                "macro_value": selected_market_macro_indicator
            }
        )

        st.plotly_chart(
            macro_compare_fig,
            use_container_width=True,
            key="macro_compare_chart"
        )

    st.markdown("### Comparison Table")

    st.dataframe(
        filtered_market_macro.sort_values("month_start", ascending=False),
        use_container_width=True,
        hide_index=True
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
            "monthly_return_pct": "SPY Monthly Return %"
        }
    )

    st.plotly_chart(
        scatter_fig,
        use_container_width=True,
        key="market_macro_scatter"
    )


#----------------------
#About this project
#----------------------
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
        - Category and ticker filters

        **Next planned feature:**

        Add macroeconomic indicators and compare them against market performance.
        """
    )

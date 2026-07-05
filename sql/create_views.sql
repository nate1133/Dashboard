-- ============================================================
-- Finance/Economics Pipeline: SQL Views
-- Database: analytics_lab
-- Schema: finance_econ
-- ============================================================

-- ------------------------------------------------------------
-- Latest stock prices with ticker metadata
-- ------------------------------------------------------------

DROP VIEW IF EXISTS finance_econ.latest_stock_prices CASCADE;

CREATE VIEW finance_econ.latest_stock_prices AS
SELECT DISTINCT ON (sp.ticker)
    sp.ticker,
    tm.name,
    tm.category,
    sp.price_date,
    sp.close_price,
    sp.adjusted_close,
    sp.volume,
    sp.loaded_at
FROM finance_econ.stock_prices sp
LEFT JOIN finance_econ.ticker_metadata tm
    ON sp.ticker = tm.ticker
ORDER BY sp.ticker, sp.price_date DESC;


-- ------------------------------------------------------------
-- Daily stock returns
-- ------------------------------------------------------------

DROP VIEW IF EXISTS finance_econ.stock_daily_returns CASCADE;

CREATE VIEW finance_econ.stock_daily_returns AS
SELECT
    sp.ticker,
    tm.name,
    tm.category,
    sp.price_date,
    sp.adjusted_close,
    LAG(sp.adjusted_close) OVER (
        PARTITION BY sp.ticker
        ORDER BY sp.price_date
    ) AS prior_adjusted_close,
    ROUND(
        (
            sp.adjusted_close / LAG(sp.adjusted_close) OVER (
                PARTITION BY sp.ticker
                ORDER BY sp.price_date
            ) - 1
        ) * 100,
        4
    ) AS daily_return_pct,
    sp.volume
FROM finance_econ.stock_prices sp
LEFT JOIN finance_econ.ticker_metadata tm
    ON sp.ticker = tm.ticker;


-- ------------------------------------------------------------
-- Stock performance summary
-- ------------------------------------------------------------

DROP VIEW IF EXISTS finance_econ.stock_performance_summary CASCADE;

CREATE VIEW finance_econ.stock_performance_summary AS
WITH ranked_prices AS (
    SELECT
        ticker,
        price_date,
        adjusted_close,
        ROW_NUMBER() OVER (
            PARTITION BY ticker
            ORDER BY price_date ASC
        ) AS first_rank,
        ROW_NUMBER() OVER (
            PARTITION BY ticker
            ORDER BY price_date DESC
        ) AS last_rank
    FROM finance_econ.stock_prices
),
first_prices AS (
    SELECT
        ticker,
        price_date AS first_date,
        adjusted_close AS first_adjusted_close
    FROM ranked_prices
    WHERE first_rank = 1
),
last_prices AS (
    SELECT
        ticker,
        price_date AS last_date,
        adjusted_close AS last_adjusted_close
    FROM ranked_prices
    WHERE last_rank = 1
)
SELECT
    l.ticker,
    tm.name,
    tm.category,
    f.first_date,
    l.last_date,
    f.first_adjusted_close,
    l.last_adjusted_close,
    ROUND(l.last_adjusted_close - f.first_adjusted_close, 4) AS dollar_change,
    ROUND(
        ((l.last_adjusted_close / f.first_adjusted_close) - 1) * 100,
        2
    ) AS total_return_pct
FROM last_prices l
JOIN first_prices f
    ON l.ticker = f.ticker
LEFT JOIN finance_econ.ticker_metadata tm
    ON l.ticker = tm.ticker;


-- ------------------------------------------------------------
-- Monthly stock returns
-- ------------------------------------------------------------

DROP VIEW IF EXISTS finance_econ.monthly_stock_returns CASCADE;

CREATE VIEW finance_econ.monthly_stock_returns AS
WITH monthly_prices AS (
    SELECT
        sp.ticker,
        tm.name,
        tm.category,
        DATE_TRUNC('month', sp.price_date)::date AS month_start,
        sp.price_date,
        sp.adjusted_close,
        ROW_NUMBER() OVER (
            PARTITION BY sp.ticker, DATE_TRUNC('month', sp.price_date)
            ORDER BY sp.price_date ASC
        ) AS first_day_rank,
        ROW_NUMBER() OVER (
            PARTITION BY sp.ticker, DATE_TRUNC('month', sp.price_date)
            ORDER BY sp.price_date DESC
        ) AS last_day_rank
    FROM finance_econ.stock_prices sp
    LEFT JOIN finance_econ.ticker_metadata tm
        ON sp.ticker = tm.ticker
),
first_prices AS (
    SELECT
        ticker,
        month_start,
        adjusted_close AS first_adjusted_close
    FROM monthly_prices
    WHERE first_day_rank = 1
),
last_prices AS (
    SELECT
        ticker,
        name,
        category,
        month_start,
        adjusted_close AS last_adjusted_close
    FROM monthly_prices
    WHERE last_day_rank = 1
)
SELECT
    l.ticker,
    l.name,
    l.category,
    l.month_start,
    f.first_adjusted_close,
    l.last_adjusted_close,
    ROUND(
        ((l.last_adjusted_close / f.first_adjusted_close) - 1) * 100,
        2
    ) AS monthly_return_pct
FROM last_prices l
JOIN first_prices f
    ON l.ticker = f.ticker
    AND l.month_start = f.month_start;


-- ------------------------------------------------------------
-- Stock risk summary
-- ------------------------------------------------------------

DROP VIEW IF EXISTS finance_econ.stock_risk_summary CASCADE;

CREATE VIEW finance_econ.stock_risk_summary AS
WITH returns AS (
    SELECT
        ticker,
        name,
        category,
        price_date,
        daily_return_pct
    FROM finance_econ.stock_daily_returns
    WHERE daily_return_pct IS NOT NULL
)
SELECT
    ticker,
    name,
    category,
    COUNT(*) AS trading_days,
    ROUND(AVG(daily_return_pct), 4) AS avg_daily_return_pct,
    ROUND(STDDEV(daily_return_pct), 4) AS daily_volatility_pct,
    ROUND(MIN(daily_return_pct), 4) AS worst_daily_return_pct,
    ROUND(MAX(daily_return_pct), 4) AS best_daily_return_pct
FROM returns
GROUP BY ticker, name, category;


-- ------------------------------------------------------------
-- Latest economic indicators
-- ------------------------------------------------------------

DROP VIEW IF EXISTS finance_econ.latest_economic_indicators CASCADE;

CREATE VIEW finance_econ.latest_economic_indicators AS
SELECT DISTINCT ON (indicator_code)
    indicator_code,
    indicator_name,
    observation_date,
    value,
    source,
    loaded_at
FROM finance_econ.economic_indicators
ORDER BY indicator_code, observation_date DESC;


-- ------------------------------------------------------------
-- Macro trends
-- ------------------------------------------------------------

DROP VIEW IF EXISTS finance_econ.macro_trends CASCADE;

CREATE VIEW finance_econ.macro_trends AS
SELECT
    indicator_code,
    indicator_name,
    observation_date,
    value,
    source
FROM finance_econ.economic_indicators
ORDER BY indicator_code, observation_date;


-- ------------------------------------------------------------
-- Market returns joined to monthly macro readings
-- ------------------------------------------------------------

DROP VIEW IF EXISTS finance_econ.market_macro_monthly CASCADE;

CREATE VIEW finance_econ.market_macro_monthly AS
WITH monthly_macro AS (
    SELECT DISTINCT ON (
        indicator_code,
        DATE_TRUNC('month', observation_date)::date
    )
        indicator_code,
        indicator_name,
        DATE_TRUNC('month', observation_date)::date AS month_start,
        value AS macro_value
    FROM finance_econ.economic_indicators
    ORDER BY
        indicator_code,
        DATE_TRUNC('month', observation_date)::date,
        observation_date DESC
)
SELECT
    msr.month_start,
    msr.ticker,
    msr.monthly_return_pct,
    mm.indicator_code,
    mm.indicator_name,
    mm.macro_value
FROM finance_econ.monthly_stock_returns msr
JOIN monthly_macro mm
    ON msr.month_start = mm.month_start
WHERE msr.ticker = 'SPY'
ORDER BY msr.month_start, mm.indicator_code;

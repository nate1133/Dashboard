# Finance & Economics Data Pipeline

A self-hosted finance and economics data pipeline built with Ubuntu Server, Docker, PostgreSQL, Python, SQL, and Streamlit.

## Project Overview

This project collects stock market data and macroeconomic indicators, stores them in PostgreSQL, creates reusable SQL views, and displays the results in a Streamlit dashboard.

The goal is to practice real-world analytics engineering and data engineering concepts using a home server environment.

## Current Features

- Stock price extraction from Yahoo Finance using `yfinance`
- Macroeconomic indicator extraction from FRED
- PostgreSQL database running in Docker
- Config-driven ticker and indicator lists
- Ticker metadata table
- SQL views for:
  - Latest stock prices
  - Daily returns
  - Monthly returns
  - Performance summary
  - Risk and volatility
  - Latest macro indicators
  - Macro trends
- Streamlit dashboard with tabs:
  - Overview
  - Returns
  - Risk & Volatility
  - Macro Indicators
  - About
- Dashboard runs as a background `systemd` service
- Scheduled ETL jobs using cron

## Tech Stack

- Ubuntu Server 22.04.5 LTS
- Docker
- PostgreSQL
- Python
- pandas
- yfinance
- SQLAlchemy
- psycopg2
- python-dotenv
- Streamlit
- Plotly
- VS Code Remote SSH
- cron
- systemd


## Dashboard Screenshots

### Overview
![Overview](assets/screenshots/overview.png)

### Returns
![Returns](assets/screenshots/returns.png)

### Risk & Volatility
![Risk](assets/screenshots/risk.png)

### Macro Indicators
![Macro](assets/screenshots/macro.png)

### Market vs Macro
![Market vs Macro](assets/screenshots/market_vs_macro.png)


## Project Structure

```text
finance-econ-pipeline/
├── app/
│   └── dashboard.py
├── config/
│   ├── tickers.csv
│   └── economic_indicators.csv
├── data/
├── logs/
├── scripts/
│   ├── load_stock_prices.py
│   ├── load_ticker_metadata.py
│   ├── load_economic_indicators.py
│   ├── run_stock_loader.sh
│   └── run_macro_loader.sh
├── sql/
│   └── create_views.sql
├── .env
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt

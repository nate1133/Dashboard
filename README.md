# Finance & Economics Data Pipeline

A self-hosted finance and economics data pipeline built with Ubuntu Server, Docker, PostgreSQL, Python, SQL, and Streamlit.

## Project Overview

This project collects stock market data and macroeconomic indicators, stores them in PostgreSQL, creates reusable SQL views, and displays the results in a Streamlit dashboard.

The goal is to practice real-world analytics engineering and data engineering concepts using a home server environment.

## Architecture

```text
Yahoo Finance                 FRED
     │                          │
     ▼                          ▼
Python ETL Scripts       Python Macro Loader
     │                          │
     └──────────────┬───────────┘
                    ▼
          PostgreSQL Database
          running in Docker
                    │
                    ▼
              SQL Views
                    │
                    ▼
          Streamlit Dashboard
                    │
                    ▼
       Local Browser / VS Code / Analysis


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

## Skills Demonstrated

- Linux server setup and administration
- Docker container management
- PostgreSQL database design
- Python ETL development
- SQL views and analytics modeling
- Cron-based automation
- Database backup scripting
- Streamlit dashboard development
- Plotly data visualization
- VS Code Remote SSH workflow
- Git and GitHub version control


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


## How to Run Locally

Activate the Python environment:

```bash
Run manually:

```bash
source venv/bin/activate
python3 -m streamlit run app/dashboard.py --server.address 0.0.0.0 --server.port 8501


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


---

## 4. Current Status section

```markdown
## Current Status

Version 1 is complete.

The project currently supports:

- Automated stock market data ingestion
- Automated macroeconomic data ingestion
- PostgreSQL storage and SQL views
- Streamlit dashboard with multiple tabs
- Local network dashboard hosting
- Scheduled cron jobs
- PostgreSQL backup automation

Future improvements may include:

- Public-safe cloud deployment
- User authentication
- Additional asset classes
- More advanced statistical modeling
- Alerts for unusual market moves
- Expanded macro/market comparison analysis
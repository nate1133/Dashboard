# Trading Intelligence Platform

Streamlit MVP for stock research, rule-based strategy signals, backtesting, and simulated paper trading.

This app does not place real-money trades. Live broker integration is intentionally absent from the MVP.

## Features

- Home dashboard for major index ETFs and watchlist symbols
- Stock research with price chart, moving averages, RSI, MACD, volume, volatility, and 52-week range
- Bullish Momentum Strategy scanner with auditable rule pass/fail output
- Historical backtesting with equity curve and trade log
- Simulated paper broker with cash, positions, trade history, and P/L tracking
- Risk manager enforcing max position size, daily trade count, emergency stop, allowed tickers, long-only stocks, no margin, and no options
- SQLite persistence for trades, positions, strategy signals, and audit logs

## What It Does Not Do

- No live trading
- No real broker API
- No options trading in the MVP
- No short selling
- No margin
- No AI-driven trade execution

## Run

From the project root:

```bash
source venv/bin/activate
python trading_platform/run_app.py
```

Then open:

```text
http://localhost:8503
```

## Structure

```text
trading_platform/
├── app.py
├── run_app.py
├── data/database/
├── src/
│   ├── backtesting/
│   ├── data/
│   ├── database/
│   ├── reporting/
│   ├── strategies/
│   ├── trading/
│   └── utils/
└── README.md
```

## Safety

Every simulated order flows through:

```text
Data -> Indicators -> Strategy Rules -> Risk Manager -> Simulated Broker -> Audit Log
```

Paper trading remains the only supported mode.

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "trading_platform" / "data"
DATABASE_DIR = DATA_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "paper_trading.sqlite"

STARTING_CASH = 100_000.00
MAX_POSITION_PCT = 0.05
MAX_DAILY_LOSS_PCT = 0.02
MAX_TRADES_PER_DAY = 5

DEFAULT_WATCHLIST = [
    "SPY",
    "QQQ",
    "DIA",
    "IWM",
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "META",
    "TSLA",
]

MAJOR_INDEX_TICKERS = ["SPY", "QQQ", "DIA", "IWM"]

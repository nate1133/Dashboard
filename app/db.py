from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
REQUIRED_DB_ENV_VARS = ("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME")


def load_database_settings() -> dict[str, str]:
    load_dotenv(ENV_PATH)

    settings = {name: os.getenv(name) for name in REQUIRED_DB_ENV_VARS}
    missing = [name for name, value in settings.items() if not value]

    if missing:
        raise RuntimeError(
            "Missing required database environment variables: "
            + ", ".join(missing)
        )

    return settings


def create_db_engine():
    settings = load_database_settings()

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=settings["DB_USER"],
        password=settings["DB_PASSWORD"],
        host=settings["DB_HOST"],
        port=int(settings["DB_PORT"]),
        database=settings["DB_NAME"],
    )

    return create_engine(url, pool_pre_ping=True)

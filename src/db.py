"""Connect to PostgreSQL using the project .env file."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import PROJECT_ROOT
from src.logger import configure_logging, get_logger

logger = get_logger(__name__)

ENV_PATH = PROJECT_ROOT / ".env"
REQUIRED_SETTINGS = (
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
)


def load_db_settings() -> dict[str, str]:
    """Read connection settings from .env. The password is not logged."""
    load_dotenv(ENV_PATH)
    missing = [name for name in REQUIRED_SETTINGS if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            f"Missing settings in {ENV_PATH}: {', '.join(missing)}"
        )
    return {name: os.environ[name] for name in REQUIRED_SETTINGS}


def connect() -> psycopg.Connection:
    """Open a PostgreSQL connection and confirm it with SELECT 1."""
    settings = load_db_settings()
    logger.info(
        "Connecting to PostgreSQL database %s at %s:%s as %s",
        settings["DB_NAME"],
        settings["DB_HOST"],
        settings["DB_PORT"],
        settings["DB_USER"],
    )
    connection = psycopg.connect(
        host=settings["DB_HOST"],
        port=int(settings["DB_PORT"]),
        dbname=settings["DB_NAME"],
        user=settings["DB_USER"],
        password=settings["DB_PASSWORD"],
        connect_timeout=5,
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    logger.info(
        "Connected to PostgreSQL database %s at %s:%s",
        settings["DB_NAME"],
        settings["DB_HOST"],
        settings["DB_PORT"],
    )
    return connection


def main() -> None:
    configure_logging()
    try:
        connection = connect()
    except Exception:
        logger.exception("PostgreSQL connection failed")
        raise SystemExit(1) from None
    connection.close()


if __name__ == "__main__":
    main()

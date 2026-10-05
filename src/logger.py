"""Shared logging for the support-ops scripts."""

from __future__ import annotations

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger once for a script entry point."""
    logging.basicConfig(level=level, format=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for a module. Names look like src.etl."""
    return logging.getLogger(name)

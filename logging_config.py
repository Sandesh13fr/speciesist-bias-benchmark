"""Logging setup utilities."""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Configure application-wide logging.

    Args:
        level: Logging level string (for example, "INFO").
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

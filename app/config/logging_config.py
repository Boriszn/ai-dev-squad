"""Logging configuration helpers for AI Dev Squad.

This module keeps logging setup in one place. The current configuration
is intentionally small and readable.
"""

from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Configure application-wide logging.

    Args:
        level: Standard Python logging level.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

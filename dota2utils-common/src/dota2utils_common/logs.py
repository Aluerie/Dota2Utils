"""Console logging for the tools: loguru with emoji level icons.

Libraries that use the standard `logging` module (steam.py, aiohttp) are routed into loguru too,
so everything is printed in the same format.
"""

from __future__ import annotations

import inspect
import logging
import sys
from typing import override

from loguru import logger

__all__ = (
    "logger",
    "setup_logging",
)

# Time, the level's emoji icon, then the message;
FORMAT = "<green>{time:HH:mm:ss}</green> {level.icon} <level>{message}</level>"

# Only "natively wide" emoji: some of loguru's default icons (info, warning) are symbols turned into emoji
# with an invisible U+FE0F character, which terminals often draw over the following space.
LEVEL_ICONS = {
    "TRACE": "🔍",
    "DEBUG": "🐞",
    "INFO": "🔹",
    "SUCCESS": "✅",
    "WARNING": "🔶",
    "ERROR": "❌",
    "CRITICAL": "💀",
}


class _InterceptHandler(logging.Handler):
    """Send records from the standard `logging` module to loguru (the recipe from loguru's README)."""

    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find the caller outside of `logging`, so loguru reports the right module;
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(level: str = "INFO") -> None:
    """Print log messages of `level` and above to the console. Call once at the start of a tool."""
    logger.remove()
    for name, icon in LEVEL_ICONS.items():
        logger.level(name, icon=icon)
    logger.add(sys.stderr, level=level, format=FORMAT)
    logging.basicConfig(handlers=[_InterceptHandler()], level=logging.INFO, force=True)

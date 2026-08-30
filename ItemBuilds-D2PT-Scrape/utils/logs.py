from __future__ import annotations

import logging
import pathlib
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator


@contextmanager
def setup_logging() -> Generator[Any, Any, Any]:
    """Setup logging."""
    log = logging.getLogger()
    log.setLevel(logging.INFO)

    try:
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)-4.4s %(name)-30s %(lineno)-4d %(funcName)-35s %(message)s",
            "%H:%M:%S %d/%m",
        )

        # Stream Handler
        handler = logging.StreamHandler()
        handler.setFormatter(fmt)
        log.addHandler(handler)

        # ensure logs folder
        pathlib.Path(".temp/").mkdir(parents=True, exist_ok=True)
        # File Handler
        file_handler = RotatingFileHandler(
            filename=".temp/items.log",
            encoding="utf-8",
            mode="w",
            maxBytes=7 * 1024 * 1024,
            backupCount=1,
        )
        file_handler.setFormatter(fmt)
        log.addHandler(file_handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for h in handlers:
            h.close()
            log.removeHandler(h)

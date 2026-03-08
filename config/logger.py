"""
Structured logging with loguru. Set LOG_JSON=1 or LOG_FORMAT=json for JSON lines (e.g. cloud/server).
"""
from __future__ import annotations

import os
import sys

_configured = False


def configure_logging(
    json_format: bool | None = None,
    level: str = "INFO",
) -> None:
    global _configured
    if _configured:
        return
    json_format = (
        json_format
        if json_format is not None
        else (os.environ.get("LOG_JSON", "").strip() in ("1", "true", "yes")
              or (os.environ.get("LOG_FORMAT", "").strip().lower() == "json"))
    )
    level = os.environ.get("LOG_LEVEL", level).strip().upper()
    try:
        import loguru
        logger = loguru.logger
        logger.remove()
        if json_format:
            logger.add(
                sys.stderr,
                format="{message}",
                serialize=True,
                level=level,
            )
        else:
            logger.add(
                sys.stderr,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[module]}</cyan> | <level>{message}</level>",
                level=level,
            )
        _configured = True
    except ImportError:
        _configured = True
        pass


def get_logger(name: str):
    """Return a logger bound with module=name. Configures loguru on first call if LOG_JSON/LOG_FORMAT set."""
    configure_logging()
    try:
        from loguru import logger
        return logger.bind(module=name)
    except ImportError:
        import logging
        return logging.getLogger(name)

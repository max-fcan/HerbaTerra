"""Application logging configuration helpers."""

from __future__ import annotations

import logging
import os
from logging.config import dictConfig
from flask import Flask
from typing import Optional
from pathlib import Path

class ShortPathFilter(logging.Filter):
    """Attach `parent_file` = '<parent>/<filename>' to log records."""

    def filter(self, record) -> bool:
        parent = os.path.basename(os.path.dirname(record.pathname))
        filename = os.path.basename(record.pathname)
        record.parent_file = f"{parent}/{filename}"
        return True


def configure_logging(
    *,
    logger_name: str,
    level: int = logging.INFO,
    log_format: str = "%(asctime)s | %(levelname)-7s | %(parent_file)s:%(lineno)-3d | %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
    log_dir: str = "logs",
    log_filename: Optional[str | Path] = None,
    max_bytes: int = 1 * 1024 * 1024,
    backup_count: int = 5,
    in_terminal: bool = True,
) -> logging.Logger:
    """
    Exhaustive logging configuration using dictConfig.
    """
    
    handlers = {}
    if in_terminal:
        handlers["console"] = {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": level,
            "filters": ["short_path"],
        }

    if log_filename:
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, Path(log_filename).with_suffix(".log"))
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "level": level,
            "filename": log_path,
            "maxBytes": max_bytes,
            "backupCount": backup_count,
            "filters": ["short_path"],
        }

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "short_path": {
                    "()": ShortPathFilter,
                }
            },
            "formatters": {
                "default": {
                    "format": log_format,
                    "datefmt": datefmt,
                }
            },
            "handlers": handlers,
            "root": {
                "handlers": list(handlers.keys()),
                "level": level,
            },
        }
    )

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Close existing handlers before removing them to avoid leaking file descriptors.
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    
    logger.debug("Logging configured for level %s", logging.getLevelName(level))
    return logger


def configure_app_logging(app: Flask) -> None:
    """Configure structured console and file logging based on app settings."""

    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    # Default format: [time] LEVEL | parent/file:line | message
    log_format = app.config.get(
        "DEFAULT_LOG_FORMAT",
        "%(asctime)s | %(levelname)-7s | %(parent_file)s:%(lineno)-3d | %(message)s",
    )
    datefmt = app.config.get("DEFAULT_LOG_DATEFMT", "%Y-%m-%d %H:%M:%S")

    log_dir = app.config.get("DEFAULT_LOG_DIR", "logs")
    log_filename = Path(app.config.get("DEFAULT_LOG_FILENAME", Path("app.log"))).with_suffix(".log")
    max_bytes = int(app.config.get("DEFAULT_LOG_MAX_BYTES", 10 * 1024 * 1024))
    backup_count = int(app.config.get("DEFAULT_LOG_BACKUP_COUNT", 5))

    os.makedirs(log_dir, exist_ok=True)

    configure_logging(
        name=app.name,
        level=level,
        log_format=log_format,
        datefmt=datefmt,
        log_dir=log_dir,
        log_filename=log_filename,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )

    # Make Flask's app.logger use the root handlers configured above.
    app_logger = app.logger  # Triggers Flask logger creation if not already created.
    app_logger.setLevel(level)
    app_logger.propagate = False
    app_logger.debug("Logging configured for level %s", level_name)


__all__ = ["configure_app_logging", "configure_logging", "ShortPathFilter"]

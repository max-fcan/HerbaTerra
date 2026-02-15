"""Application logging configuration."""

from __future__ import annotations

import logging
import os
from logging.config import dictConfig
from pathlib import Path

from flask import Flask


class ShortPathFilter(logging.Filter):
    """Attach ``parent_file`` = ``<parent>/<filename>`` to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        parent = os.path.basename(os.path.dirname(record.pathname))
        filename = os.path.basename(record.pathname)
        record.parent_file = f"{parent}/{filename}"  # type: ignore[attr-defined]
        return True


def init_logging(app: Flask) -> None:
    """Configure structured console + rotating-file logging for *app*."""
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    log_format = app.config.get(
        "DEFAULT_LOG_FORMAT",
        "%(asctime)s | %(levelname)-7s | %(parent_file)s:%(lineno)-3d | %(message)s",
    )
    datefmt = app.config.get("DEFAULT_LOG_DATEFMT", "%Y-%m-%d %H:%M:%S")

    log_dir = str(app.config.get("DEFAULT_LOG_DIR", "logs"))
    log_filename = Path(app.config.get("DEFAULT_LOG_FILENAME", "app.log")).with_suffix(".log")
    max_bytes = int(app.config.get("DEFAULT_LOG_MAX_BYTES", 10 * 1024 * 1024))
    backup_count = int(app.config.get("DEFAULT_LOG_BACKUP_COUNT", 5))

    os.makedirs(log_dir, exist_ok=True)

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"short_path": {"()": ShortPathFilter}},
            "formatters": {
                "default": {"format": log_format, "datefmt": datefmt},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": level,
                    "filters": ["short_path"],
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "default",
                    "level": level,
                    "filename": os.path.join(log_dir, str(log_filename)),
                    "maxBytes": max_bytes,
                    "backupCount": backup_count,
                    "filters": ["short_path"],
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": level,
            },
        }
    )

    app.logger.setLevel(level)
    app.logger.debug("Logging configured – level %s", level_name)

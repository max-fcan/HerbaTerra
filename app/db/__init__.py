# Version avec le 'threading' implementé par l'IA pour pouvoir gérer le bootstrap en arrière-plan.

from __future__ import annotations

import logging
import threading

from flask import Flask

from .connections import close_local_db
from .bootstrap import (
    bootstrap_local_replica_from_app,
    get_bootstrap_status,
    update_app_bootstrap_status,
)

__all__ = ["init_db", "get_bootstrap_status", "update_app_bootstrap_status"]

_bootstrap_thread_lock = threading.Lock()
_bootstrap_thread: threading.Thread | None = None
log = logging.getLogger(__name__)


def _bootstrap_worker(app: Flask) -> None:
    log.debug("Replica bootstrap worker started.")
    try:
        result = bootstrap_local_replica_from_app(app)
        log.debug(
            "Replica bootstrap worker finished: success=%s duration=%.3fs local_db_path=%s error=%s",
            result.success,
            result.duration_seconds,
            result.local_db_path,
            result.error_message,
        )
    except Exception as exc:
        app.logger.exception("Failed to bootstrap local replica.")
        update_app_bootstrap_status(STATUS="error", ERROR_MESSAGE=str(exc))


def init_db(app: Flask) -> None:
    global _bootstrap_thread
    log.debug("Initializing DB bootstrap orchestration.")
    app.teardown_appcontext(close_local_db)
    log.info("Starting database bootstrap. \033[31mThis may take up to a few minutes on first run.\033[0m")
    with _bootstrap_thread_lock:
        if _bootstrap_thread is not None and _bootstrap_thread.is_alive():
            log.debug("Bootstrap thread is already running; skipping new thread start.")
            return

        current_status = get_bootstrap_status().STATUS
        if current_status in {"ready", "starting", "syncing"}:
            log.debug(
                "Skipping bootstrap thread start because current status is '%s'.",
                current_status,
            )
            return

        update_app_bootstrap_status(STATUS="idle", ERROR_MESSAGE=None)
        log.debug("Launching replica bootstrap thread from status '%s'.", current_status)
        _bootstrap_thread = threading.Thread(
            target=_bootstrap_worker,
            args=(app,),
            name="replica-bootstrap",
            daemon=True,
        )
        _bootstrap_thread.start()

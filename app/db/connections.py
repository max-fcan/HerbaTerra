from __future__ import annotations

import logging
import sqlite3
from flask import current_app, g
from typing import cast

from .bootstrap import get_bootstrap_status, BootstrapState

_REPLICA_STATUS_MESSAGES: dict[BootstrapState, str] = {
    "idle": "Replica bootstrap has not started yet.",
    "starting": "Preparing local embedded replica...",
    "syncing": "Syncing local embedded replica data...",
    "ready": "Local embedded replica is ready.",
    "already_exists": "Local embedded replica already exists.",
    "error": "Local embedded replica failed to initialize.",
    "unknown": "Replica state is unknown.",
}
log = logging.getLogger(__name__)
_last_reported_state: BootstrapState | None = None


def is_replica_ready() -> bool:
    return get_bootstrap_status().STATUS in ["ready", "already_exists"]


def get_replica_status() -> dict[str, str | None]:
    global _last_reported_state
    status = get_bootstrap_status()
    state: BootstrapState = cast(BootstrapState, status.STATUS)
    if state != _last_reported_state:
        log.debug("Replica status observed: state=%s error=%s", state, status.ERROR_MESSAGE)
        _last_reported_state = state
    return {
        "state": state,
        "message": _REPLICA_STATUS_MESSAGES.get(state, _REPLICA_STATUS_MESSAGES["unknown"]),
        "error": status.ERROR_MESSAGE,
    }


def get_local_db() -> sqlite3.Connection:
    if not is_replica_ready():
        replica_status = get_replica_status()
        log.warning(
            "Blocked local DB connection because replica is not ready (state=%s).",
            replica_status["state"],
        )
        raise RuntimeError(
            f"Local replica is not ready (state={replica_status['state']})."
        )

    if not hasattr(g, "db"):
        log.debug("Opening SQLite connection to local replica at %s.", current_app.config["LOCAL_DB_PATH"])
        conn = sqlite3.connect(current_app.config["LOCAL_DB_PATH"])
        conn.row_factory = sqlite3.Row
        g.db = conn

    return cast(sqlite3.Connection, g.db)


def close_local_db(_error: BaseException | None = None) -> None:
    db = cast(sqlite3.Connection | None, getattr(g, "db", None)) # Made by AI, made for safety. We check if g.db exists and is a sqlite3.Connection before trying to close it.
    if db is not None:
        db.close()
        log.debug("Closed SQLite connection for local replica.")
        del g.db

"""
Centralised DuckDB connection management.

Two access patterns:
  1. ``connect()``  – context-manager that opens **and closes** a read-only
     connection per call. Ideal for request-scoped work (catalogue queries).
  2. ``get_persistent()`` – returns a long-lived, module-level connection
     guarded by a threading lock. Ideal for the challenge service which does
     many small random reads and benefits from connection reuse.
"""

from __future__ import annotations

import duckdb
from contextlib import contextmanager
from threading import Lock
from typing import Generator

DB_PATH = "data/gbif_plants.duckdb"

# ── Persistent (long-lived) connection ──────────────────────────────────────
_PERSISTENT_CONN: duckdb.DuckDBPyConnection | None = None
_PERSISTENT_LOCK = Lock()


def get_persistent() -> tuple[duckdb.DuckDBPyConnection, Lock]:
    """Return ``(connection, lock)`` for the shared persistent connection.

    Callers **must** acquire the lock before executing queries::

        conn, lock = get_persistent()
        with lock:
            result = conn.execute("SELECT …").fetchone()
    """
    global _PERSISTENT_CONN
    if _PERSISTENT_CONN is None:
        _PERSISTENT_CONN = duckdb.connect(DB_PATH, read_only=True)
    return _PERSISTENT_CONN, _PERSISTENT_LOCK


# ── Per-request (short-lived) connection ────────────────────────────────────

@contextmanager
def connect() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Yield a read-only DuckDB connection, closing it on exit.

    Usage::

        from app.services.db import connect

        with connect() as conn:
            rows = conn.execute("SELECT …").fetchall()
    """
    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        yield conn
    finally:
        conn.close()

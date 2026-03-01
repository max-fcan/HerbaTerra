# Version avec le 'threading' implementé par l'IA pour pouvoir gérer le bootstrap en arrière-plan.

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from urllib.parse import urlparse

from flask import Flask

BootstrapState = Literal["idle", "starting", "syncing", "ready", "error", "already_exists", "unknown"]
log = logging.getLogger(__name__)


@dataclass
class BootstrapStatus:
    STATUS: BootstrapState = "idle"
    ERROR_MESSAGE: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.STATUS,
            "error_message": self.ERROR_MESSAGE,
        }


_bootstrap_status = BootstrapStatus()
_bootstrap_status_lock = Lock()


def get_bootstrap_status() -> BootstrapStatus:
    with _bootstrap_status_lock:
        return BootstrapStatus(
            STATUS=_bootstrap_status.STATUS,
            ERROR_MESSAGE=_bootstrap_status.ERROR_MESSAGE,
        )

def update_bootstrap_status(__bootstrapStatus: BootstrapStatus, **kwargs: str | None) -> None:
    with _bootstrap_status_lock:
        previous_status = __bootstrapStatus.STATUS
        previous_error = __bootstrapStatus.ERROR_MESSAGE
        for key, value in kwargs.items():
            if hasattr(__bootstrapStatus, key):
                setattr(__bootstrapStatus, key, value)
        scope = "app" if __bootstrapStatus is _bootstrap_status else f"instance:{id(__bootstrapStatus)}"
        if previous_status != __bootstrapStatus.STATUS:
            log.debug(
                "Replica bootstrap status changed (%s): %s -> %s",
                scope,
                previous_status,
                __bootstrapStatus.STATUS,
            )
        if previous_error != __bootstrapStatus.ERROR_MESSAGE:
            if __bootstrapStatus.ERROR_MESSAGE:
                log.error(
                    "Replica bootstrap error updated (%s): %s",
                    scope,
                    __bootstrapStatus.ERROR_MESSAGE,
                )
            elif previous_error:
                log.debug("Replica bootstrap error cleared (%s).", scope)

def update_app_bootstrap_status(**kwargs: str | None) -> None:
    update_bootstrap_status(_bootstrap_status, **kwargs)

@dataclass(frozen=True)
class BootstrapResult:
    success: bool
    local_db_path: str | None
    sync_url: str
    started_at: str
    finished_at: str
    duration_seconds: float
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _get_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_sync_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return "<invalid-sync-url>"
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def bootstrap_local_replica(
    local_db_path: str | Path,
    sync_url: str,
    auth_token: str,
    _bootstrapStatus: BootstrapStatus,
    override: bool = False
) -> BootstrapResult:
    url = (sync_url or "").strip()
    auth_token = (auth_token or "").strip()
    local_db_path = Path(local_db_path)

    log.debug(
        "Starting replica bootstrap flow: local_db_path=%s override=%s sync_url=%s",
        local_db_path,
        override,
        _safe_sync_url(url),
    )
    
    if not url:
        log.error("Replica bootstrap failed validation: TURSO_DATABASE_URL is empty.")
        raise RuntimeError("TURSO_DATABASE_URL is required for embedded replica sync.")
    if not auth_token:
        log.error("Replica bootstrap failed validation: TURSO_AUTH_TOKEN is empty.")
        raise RuntimeError("TURSO_AUTH_TOKEN is required for embedded replica sync.")

    if local_db_path.exists() and not override:
        log.debug(
            "Replica bootstrap skipped because local database already exists at %s.",
            local_db_path,
        )
        update_bootstrap_status(_bootstrapStatus, STATUS="already_exists", ERROR_MESSAGE=None)
        return BootstrapResult(
            success=True,
            local_db_path=str(local_db_path),
            sync_url=url,
            started_at=_get_time(),
            finished_at=_get_time(),
            duration_seconds=0.0,
            error_message=None,
        )
    local_db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from libsql import connect # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency
        log.exception("Replica bootstrap cannot start because libsql is not installed.", exc_info=exc)
        raise RuntimeError("libsql is not installed. Run `pip install libsql`.") from exc
    
    started_at = _get_time()
    update_bootstrap_status(_bootstrapStatus, STATUS="starting", ERROR_MESSAGE=None)
    log.debug("Connecting embedded replica client to local file %s.", local_db_path)

    try:
        conn = connect(
            str(local_db_path),
            sync_url=url,
            auth_token=auth_token,
            offline=False,
        )
    except ValueError as exc:
        log.exception("Failed to connect to embedded replica. This may be due to network issues or incorrect configuration.", exc_info=exc)
        log.error("Failed to connect to embedded replica. \n * Are you sure you are online ? \n * If this error persists, please contact owner at m.tanguy@ifs.edu.sg")
        update_bootstrap_status(_bootstrapStatus, STATUS="error", ERROR_MESSAGE="Failed to connect to embedded replica. Are you sure you are online ? If this error persists, please contact owner at m.tanguy@ifs.edu.sg")
        finished_at = _get_time()
        return BootstrapResult(
            success=False,
            local_db_path=None,
            sync_url=url,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=(datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)).total_seconds(),
            error_message="Failed to connect to embedded replica. Are you sure you are online ?",
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to connect to embedded replica: {exc}") from exc

    try:
        update_bootstrap_status(_bootstrapStatus, STATUS="syncing")
        log.debug("Sync started for local embedded replica.")
        conn.sync()
        log.debug("Sync completed for local embedded replica.")
    except Exception as exc:
        log.exception("Replica sync failed.", exc_info=exc)
        update_bootstrap_status(_bootstrapStatus, STATUS="error", ERROR_MESSAGE=str(exc))
        finished_at = _get_time()
        return BootstrapResult(
            success=False,
            local_db_path=None,
            sync_url=url,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=(
                datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)
            ).total_seconds(),
            error_message=str(exc),
        )
    finally:
        conn.close()
        log.debug("Closed embedded replica connection.")

    finished_at = _get_time()
    update_bootstrap_status(_bootstrapStatus, STATUS="ready", ERROR_MESSAGE=None)
    duration_seconds = (
        datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)
    ).total_seconds()
    log.info(
        "Replica bootstrap completed successfully in %.3fs (local_db_path=%s).",
        duration_seconds,
        local_db_path,
    )

    return BootstrapResult(
        success=True,
        local_db_path=str(local_db_path),
        sync_url=url,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
    )


def bootstrap_local_replica_from_app(app: Flask) -> BootstrapResult:
    global _bootstrap_status
        
    sync_url = _first_non_empty_config(
        app,
        "TURSO_DATABASE_URL",
        "TURSO100_DATABASE_URL",
    )
    auth_token = _first_non_empty_config(
        app,
        "TURSO_AUTH_TOKEN",
        "TURSO100_AUTH_TOKEN",
    )
    log.info(
        "Bootstrap requested from Flask app with local_db_path=%s.",
        app.config["LOCAL_DB_PATH"],
    )
    result = bootstrap_local_replica(
        local_db_path=app.config["LOCAL_DB_PATH"],
        sync_url=sync_url,
        auth_token=auth_token,
        _bootstrapStatus=_bootstrap_status,
    )
    # User logs
    log.info(
        "Bootstrap completed.\n * Typically runs on %s\n * If it doesn't work, wait a bit and refresh, or try %s",
        f"http://127.0.0.1:{app.config.get('PORT', 5000)}",
        f"http://localhost:{app.config.get('PORT', 5000)}",
    )
    return result

def _first_non_empty_config(app: Flask, *keys: str) -> str:
    """
    Fonction utilitaire pour récupérer la première valeur de configuration non vide parmi une liste de clés présélectionnées.
    """
    for key in keys:
        value = str(app.config.get(key, "")).strip()
        if value:
            return value
    return ""
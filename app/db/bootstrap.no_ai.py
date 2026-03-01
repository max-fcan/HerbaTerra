from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from flask import Flask

BootstrapState = Literal["idle", "starting", "syncing", "ready", "already_exists", "error", "unknown"]

class BootstrapStatus:
    STATUS: BootstrapState = "unknown"
    ERROR_MESSAGE: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.STATUS,
            "error_message": self.ERROR_MESSAGE,
        }

bootstrapStatus = BootstrapStatus()

def get_bootstrap_status() -> BootstrapStatus:
    return bootstrapStatus

def update_bootstrap_status(_bootstrapStatus: BootstrapStatus, **kwargs: str | None) -> None:
    for key, value in kwargs.items():
        if hasattr(_bootstrapStatus, key):
            setattr(_bootstrapStatus, key, value)


@dataclass(frozen=True)
class BootstrapResult:
    success: bool
    local_db_path: str | None
    sync_url: str
    started_at: str
    finished_at: str
    duration_seconds: float
    error_message: str | None = None
    already_exists: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _get_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def bootstrap_local_replica(
    local_db_path: str | Path,
    sync_url: str,
    auth_token: str,
    _bootstrapStatus: BootstrapStatus,
    override: bool = False
) -> BootstrapResult:
    url = (sync_url or "").strip()
    auth_token = (auth_token or "").strip()
    
    if not url:
        raise RuntimeError("TURSO_DATABASE_URL is required for embedded replica sync.")
    if not auth_token:
        raise RuntimeError("TURSO_AUTH_TOKEN is required for embedded replica sync.")
    
    local_db_path = Path(local_db_path)
    
    if local_db_path.exists() and not override:
        update_bootstrap_status(_bootstrapStatus, STATUS="already_exists", ERROR_MESSAGE=None)
        return BootstrapResult(
            success=True,
            local_db_path=str(local_db_path),
            sync_url=url,
            started_at=_get_time(),
            finished_at=_get_time(),
            duration_seconds=0.0,
            already_exists=True,
        )
    local_db_path.parent.mkdir(parents=True, exist_ok=True)

    update_bootstrap_status(_bootstrapStatus, STATUS="idle", ERROR_MESSAGE=None)

    try:
        from libsql import connect # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError("libsql is not installed. Run `pip install libsql`.") from exc

    started_at = _get_time()
    update_bootstrap_status(_bootstrapStatus, STATUS="starting", ERROR_MESSAGE=None)

    try:
        conn = connect(
            str(local_db_path),
            sync_url=url,
            auth_token=auth_token,
            offline=False,
        )
    except ValueError as e:
        raise RuntimeError("Failed to connect to embedded replica. Are you sure you are online ?") from e
    except Exception as exc:
        raise RuntimeError(f"Failed to connect to embedded replica: {exc}") from exc

    try:
        update_bootstrap_status(_bootstrapStatus, STATUS="syncing")
        conn.sync()
    except Exception as exc:
        update_bootstrap_status(_bootstrapStatus, STATUS="error", ERROR_MESSAGE=str(exc))
        finished_at = _get_time()
        return BootstrapResult(
            success=False,
            local_db_path=None,
            sync_url=url,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=(datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)).total_seconds(),
            error_message=str(exc),
        )
    finally:
        conn.close()

    finished_at = _get_time()
    update_bootstrap_status(_bootstrapStatus, STATUS="ready")

    started_dt = datetime.fromisoformat(started_at)
    finished_dt = datetime.fromisoformat(finished_at)
    return BootstrapResult(
        success=True,
        local_db_path=str(local_db_path),
        sync_url=url,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=(finished_dt - started_dt).total_seconds(),
    )


def bootstrap_local_replica_from_app(app: Flask) -> BootstrapResult:
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

    global bootstrapStatus
    return bootstrap_local_replica(
        local_db_path=app.config["LOCAL_DB_PATH"],
        sync_url=sync_url,
        auth_token=auth_token,
        _bootstrapStatus=bootstrapStatus
    )


def _first_non_empty_config(app: Flask, *keys: str) -> str:
    for key in keys:
        value = str(app.config.get(key, "")).strip()
        if value:
            return value
    return ""
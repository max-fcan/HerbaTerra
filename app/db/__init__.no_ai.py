from flask import Flask

from .connections import close_local_db
from .bootstrap import (
    bootstrap_local_replica_from_app,
    get_bootstrap_status,
    update_bootstrap_status,
)

__all__ = ["init_db", "get_bootstrap_status"]


def init_db(app: Flask) -> None:
    app.teardown_appcontext(close_local_db)
    try:
        bootstrap_local_replica_from_app(app)
    except Exception as exc:
        app.logger.exception("Failed to bootstrap local replica.")
        update_bootstrap_status(STATUS="error", ERROR_MESSAGE=str(exc))

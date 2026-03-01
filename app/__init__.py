from flask import Flask, jsonify, redirect, request, url_for

from app.config import Config
from .db.connections import get_replica_status, is_replica_ready
from .logging_setup import setup_logging
from .db import init_db
from .routes import register_routes


def _human_number(value):
    """Jinja filter: 54260 → '54.3K', 1200000 → '1.2M', 830 → '830'."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return value
    if n >= 1_000_000:
        formatted = f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{formatted}M"
    if n >= 1_000:
        formatted = f"{n / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{formatted}K"
    return str(n)


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    setup_logging(
        app.config.get("LOG_LEVEL", "INFO"),
        str(app.config.get("LOG_FILE", "logs/app.log")),
        app.config.get("WERKZEUG_LOG_LEVEL", "WARNING")
    )

    app.jinja_env.filters["human_number"] = _human_number # Implémenté par l'IA, pour formater les nombres de manière plus lisible dans les templates Jinja.

    init_db(app)
    register_routes(app)

    @app.before_request # Implémenté par l'IA, pour restreindre l'accès aux routes tant que la réplica n'est pas prête, pour éviter le risque de corruption de la base de données locale.
    def gate_routes_until_replica_ready():
        endpoint = request.endpoint or ""
        if endpoint in {"static", "pages.index", "pages.start", "api.replica_status_api"}:
            return None

        if is_replica_ready():
            return None

        if endpoint.startswith("api."):
            return jsonify(get_replica_status()), 503

        return redirect(url_for("pages.start"))

    return app

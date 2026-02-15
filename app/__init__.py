from flask import Flask
from config.config import Config
from app.log import init_logging


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Logging
    init_logging(app)

    # Blueprints
    from app.routes import landing_bp, game_bp, catalogue_bp
    from app.api import api_bp

    app.register_blueprint(landing_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(catalogue_bp)
    app.register_blueprint(api_bp)

    # ── Caching headers for static assets ──────────────────────────────
    @app.after_request
    def add_cache_headers(response):
        if response.content_type and (
            "text/css" in response.content_type
            or "application/javascript" in response.content_type
            or "image/" in response.content_type
            or "font/" in response.content_type
        ):
            response.cache_control.max_age = 2592000  # 30 days
            response.cache_control.public = True

        if response.content_type and "text/html" in response.content_type:
            response.cache_control.no_cache = True
            response.cache_control.no_store = True
            response.add_etag()

        return response

    return app

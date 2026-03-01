from flask import Flask

from .api import bp as api_bp
from .catalogue import bp as catalogue_bp
from .geojson import bp as geo_bp
from .health import bp as health_bp
from .pages import bp as pages_bp
from .play import bp as play_bp

def register_routes(app: Flask) -> None:
    app.register_blueprint(pages_bp)
    app.register_blueprint(play_bp)
    app.register_blueprint(catalogue_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(geo_bp)
    app.register_blueprint(health_bp)

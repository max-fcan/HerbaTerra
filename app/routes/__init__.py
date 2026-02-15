"""Routes package — Blueprint imports and exports."""

from app.routes.landing import landing_bp
from app.routes.game import game_bp
from app.routes.catalogue import catalogue_bp

__all__ = ["landing_bp", "game_bp", "catalogue_bp"]
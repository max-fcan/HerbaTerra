"""API package — JSON endpoints under ``/api/``."""

from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Import sub-modules so their routes are registered on api_bp.
from app.api import game as _game  # noqa: F401, E402
from app.api import catalogue as _catalogue  # noqa: F401, E402

import logging
from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)
log = logging.getLogger(__name__)

@bp.get("/health")
def health():
    """Health endpoint used to verify that the application is running."""
    log.info("health check")
    return jsonify(status="ok")

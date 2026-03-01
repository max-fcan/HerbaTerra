import logging
from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)
log = logging.getLogger(__name__)

@bp.get("/health")
def health():
    """Endpoint de santé pour vérifier que l'application fonctionne."""
    log.info("health check")
    return jsonify(status="ok")
"""Game API — next challenge endpoint."""

from flask import jsonify

from app.api import api_bp


@api_bp.route("/game/next")
def next_challenge():
    """Return the next challenge as JSON."""
    from app.services.challenge import Challenge

    challenge = Challenge()
    if not challenge.url:
        return jsonify({"challenge": None}), 404
    return jsonify({"challenge": challenge.to_dict()})

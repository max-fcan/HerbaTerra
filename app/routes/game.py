"""Game blueprint — the plant guessing game (hub, play, country)."""

from flask import Blueprint, render_template, request

game_bp = Blueprint("game", __name__, url_prefix="/game")


@game_bp.route("/")
def index():
    """Game hub — world map + links to play and catalogue."""
    return render_template("game/index.html")


@game_bp.route("/play")
def play():
    """Start a new challenge round."""
    from app.services.challenge import Challenge

    challenge = Challenge().to_dict()
    return render_template("game/play.html", challenge=challenge)


@game_bp.route("/country")
def country():
    """Country detail page (reached from the world map)."""
    country_name = request.args.get("name", "Unknown")
    country_code = request.args.get("code", "")
    return render_template(
        "game/country.html",
        country_name=country_name,
        country_code=country_code,
    )

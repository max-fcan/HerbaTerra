from flask import Blueprint, jsonify, render_template

play_bp = Blueprint('play', __name__, url_prefix='/play')

from app.services.challenges import Challenge



@play_bp.route('')
@play_bp.route('/')
def index():
    """Play index page"""
    return render_template('play/index.html')


@play_bp.route('/daily')
def daily():
    """Daily challenge page"""
    challenge = Challenge().to_dict()
    return render_template('play/daily_game_v7.html', challenge=challenge)


@play_bp.route('/daily/next')
def daily_next():
    """Return the next daily challenge as JSON."""
    challenge = Challenge()
    if not challenge.url:
        return jsonify({"challenge": None}), 404
    return jsonify({"challenge": challenge.to_dict()})


@play_bp.route('/game')
def game():
    """Game page"""
    return render_template('play/game.html')


@play_bp.route('/map')
def map():
    """Map page"""
    return render_template('play/map.html')


@play_bp.route('/tournaments')
def tournaments():
    """Tournaments page"""
    return render_template('play/tournaments.html')

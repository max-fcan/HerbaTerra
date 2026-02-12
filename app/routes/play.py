from flask import Blueprint, render_template

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
    challenge = Challenge()

    print(challenge.url)
    print(challenge.solution)
    print(challenge.proposed_locations)
    return render_template('play/daily_game_v7.html', challenge=challenge)


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
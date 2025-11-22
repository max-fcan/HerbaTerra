from flask import Blueprint, render_template

play_bp = Blueprint('play', __name__, url_prefix='/play')


@play_bp.route('')
@play_bp.route('/')
def index():
    """Play index page"""
    return render_template('play/index.html')


@play_bp.route('/daily')
def daily():
    """Daily challenge page"""
    return render_template('play/daily.html')


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
from flask import Blueprint, render_template

quiz_bp = Blueprint('quiz', __name__, url_prefix='/quiz')


@quiz_bp.route('')
@quiz_bp.route('/')
def index():
    """Quiz index page"""
    return render_template('quiz/index.html')


@quiz_bp.route('/catalogue')
def catalogue():
    """Quiz catalogue page"""
    return render_template('quiz/catalogue.html')


@quiz_bp.route('/play')
def play():
    """Quiz play page"""
    return render_template('quiz/play.html')

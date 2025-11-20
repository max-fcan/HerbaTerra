from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@main_bp.route('/about')
def about():
    """About page (kept for backward compatibility)"""
    return render_template('play/index.html')

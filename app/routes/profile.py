from flask import Blueprint, render_template

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


@profile_bp.route('')
@profile_bp.route('/')
def index():
    """Profile index page"""
    return render_template('profile/index.html')


@profile_bp.route('/settings')
def settings():
    """Profile settings page"""
    return render_template('profile/settings.html')


@profile_bp.route('/statistics')
def statistics():
    """Profile statistics page"""
    return render_template('profile/statistics.html')

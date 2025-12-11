from flask import Blueprint, render_template

home_bp = Blueprint('home', __name__, url_prefix='/home')

@home_bp.route('')
@home_bp.route('/')
def home():
    """Home page with photo gallery"""
    return render_template('home/index.html', background_quality='medium')
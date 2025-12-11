"""Routes package - Blueprint imports and exports"""
from app.routes.main import main_bp
from app.routes.play import play_bp
from app.routes.profile import profile_bp
from app.routes.quiz import quiz_bp
from app.routes.home import home_bp

__all__ = ['main_bp', 'play_bp', 'profile_bp', 'quiz_bp', 'home_bp']
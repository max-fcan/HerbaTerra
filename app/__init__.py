from flask import Flask
from config.config import Config

def create_app(config_class=Config):
    """Application factory function"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Register blueprints
    from app.routes import main_bp, play_bp, profile_bp, quiz_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(play_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(quiz_bp)
    
    return app

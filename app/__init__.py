from flask import Flask
from config.config import Config
from app.logging_config import configure_app_logging

def create_app(config_class=Config):
    """Application factory function"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging before any extensions initialise.
    configure_app_logging(app)

    # Register blueprints
    from app.routes import main_bp, play_bp, profile_bp, quiz_bp, home_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(play_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(home_bp)
    
    return app

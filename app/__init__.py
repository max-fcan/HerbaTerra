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
    
    # ── Caching headers for performance ────────────────────────────────────
    @app.after_request
    def add_cache_headers(response):
        """Add HTTP caching headers for static assets"""
        # Cache static assets for 30 days
        if response.content_type and (
            'text/css' in response.content_type or
            'application/javascript' in response.content_type or
            'image/' in response.content_type or
            'font/' in response.content_type
        ):
            response.cache_control.max_age = 2592000  # 30 days
            response.cache_control.public = True
        
        # Don't cache API/HTML responses
        if response.content_type and 'text/html' in response.content_type:
            response.cache_control.no_cache = True
            response.cache_control.no_store = True
            response.add_etag()
        
        # Enable gzip compression in production
        if not app.debug:
            response.headers['Content-Encoding'] = 'gzip'
        
        return response
    
    return app

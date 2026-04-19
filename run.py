from app import create_app
from app.config import DevelopmentConfig, TestConfig, ProductionConfig

if __name__ == "__main__":
    app = create_app(ProductionConfig)  # Change to DevelopmentConfig or TestConfig as needed
    app.run(  # Start the Flask server
        host="0.0.0.0",
        port=app.config.get("PORT", 5000),
        debug=app.config.get("DEBUG", False),  # Set to True to see more detailed logs
        use_reloader=app.config.get("DEBUG", False),  # Use during development to auto-reload when files change
    )
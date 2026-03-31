from app import create_app
from app.config import ProductionConfig, TestConfig

if __name__ == "__main__":
    app = create_app(ProductionConfig)
    app.run(  # Start the Flask server
        host="0.0.0.0",
        port=app.config.get("PORT", 5000),
        debug=app.config.get("DEBUG", False),  # Set to True to see more detailed logs
        use_reloader=app.config.get("DEBUG", False),  # Use during development to auto-reload when files change
    )
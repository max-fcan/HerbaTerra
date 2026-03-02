from app import create_app
from app.config import ProductionConfig, TestConfig

if __name__ == "__main__":
    app = create_app(ProductionConfig)
    app.run(                            # Lancer le serveur Flask
        host="0.0.0.0",
        port=app.config.get("PORT", 5000),
        debug=app.config.get("DEBUG", False),   # Mettre à True pour voir les logs plus précis
        use_reloader=app.config.get("DEBUG", False),    # Utiliser pendant la phase de développement pour reloader automatiquement quand il y a des modifications
    )
import os
from app import create_app
from config.config import DevelopmentConfig

if __name__ == '__main__':
    app = create_app(DevelopmentConfig)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

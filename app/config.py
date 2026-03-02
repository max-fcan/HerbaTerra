import os
from pathlib import Path
from dotenv import load_dotenv

DEVELOPMENT_ENV = ".env"
PRODUCTION_ENV = ".env.production"

def _env_path(name: str, default: Path) -> Path:
    """Get an environment variable as a Path. If the variable is not set, return the default. If the variable is set but empty, also return the default."""
    raw = (os.getenv(name) or "").strip()
    return Path(raw) if raw else default


def _env_bool(name: str, default: bool) -> bool:
    """Get an environment variable as a boolean. Recognizes '1', 'true', 'yes', 'on' as True and '0', 'false', 'no', 'off' as False. If the variable is not set or cannot be interpreted as a boolean, return the default."""
    raw = (os.getenv(name) or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return default


def _env_int(name: str, default: int) -> int:
    """Get an environment variable as an integer. If the variable is not set or cannot be converted to an integer, return the default."""
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Get an environment variable as a float. If invalid or missing, return the default."""
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_choice(name: str, default: str, allowed: set[str]) -> str:
    """
    Get an environment variable as a choice from a set of allowed values.
    If the variable is not set or not in the allowed set, return the default.
    """
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    if raw in allowed:
        return raw
    return default


class Config:
    BASE_DIR = Path(__file__).resolve().parents[1]  # project root, wherever it is

    load_dotenv(Path(BASE_DIR) / PRODUCTION_ENV)  # TODO: change to PRODUCTION_ENV in production
        
    # ================ Application Settings ================
    SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
    PORT = _env_int("PORT", 5000)
    DEBUG = _env_bool("FLASK_DEBUG", False)

    # ================ Logging Settings ================
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()
    LOG_DIR = _env_path("LOG_DIR", BASE_DIR / "logs")
    LOG_FILE = _env_path("LOG_FILE", LOG_DIR / "app.log")

    # ================ Directory and File Paths ================
    DATA_DIR = _env_path("DATA_DIR", BASE_DIR / "data")
    LOCAL_DB_PATH = _env_path("LOCAL_DB_PATH", BASE_DIR / "temp" / "plants.db")


    # ================ Turso Database Settings ================
    TURSO500_DATABASE_URL = os.getenv("TURSO500_DATABASE_URL", "")
    TURSO500_AUTH_TOKEN = os.getenv("TURSO500_AUTH_TOKEN", "")
    TURSO100_DATABASE_URL = os.getenv("TURSO100_DATABASE_URL", "")
    TURSO100_AUTH_TOKEN = os.getenv("TURSO100_AUTH_TOKEN", "")

    # Define available resolutions and their corresponding files
    _MAP_GEOJSON_FILES = {
        "high": "countries_high_resolution.geojson",
        "medium": "countries_medium_resolution.geojson",
        "low": "countries_low_resolution.geojson",
    }
    
    MAP_GEOJSON_RESOLUTION = _env_choice("MAP_GEOJSON_RESOLUTION", "medium", set(_MAP_GEOJSON_FILES.keys()))
    MAP_GEOJSON_FILE = _MAP_GEOJSON_FILES[MAP_GEOJSON_RESOLUTION]

    # ================ Play Settings ================
    PLAY_ROUNDS = _env_int("PLAY_ROUNDS", 4)
    PLAY_GUESS_SECONDS = _env_int("PLAY_GUESS_SECONDS", 60)
    PLAY_REVEAL_AFTER_SUBMIT = _env_bool("PLAY_REVEAL_AFTER_SUBMIT", True)
    PLAY_WORLD_ANTARCTICA_PROBABILITY = _env_float("PLAY_WORLD_ANTARCTICA_PROBABILITY", 0.05)

    WERKZEUG_LOG_LEVEL = "INFO"


class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"

    LOCAL_DB_PATH = Config.BASE_DIR / "temp" / "plants.db"  # Use a separate local DB for development


class TestConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"
        
    
class ProductionConfig(Config):
    DEBUG = False
    LOG_LEVEL = "INFO"
    
    WERKZEUG_LOG_LEVEL = "WARNING"  # Reduce noisy request logs

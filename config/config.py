"""Configuration classes for different environments.

This module defines simple configuration classes that can be used to
configure the Flask application. Environment variables provide the
values for sensitive settings like the secret key and third‑party
tokens. For most users the defaults defined here are sufficient and
can be overridden by setting the respective variables in your shell
or `.env` file.
"""

import os


class Config:
    """Base configuration class with default settings."""

    # Application settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False
    
    
    # Database settings
    APP_DB_PATH = os.environ.get("APP_DB_PATH", "instance/app.db") or os.environ.get("APP_DB", "instance/app.db")
    
    
    # Third‑party API tokens
    MAPILLARY_ACCESS_TOKEN = os.environ.get("MAPILLARY_ACCESS_TOKEN") or os.environ.get("MPY_ACCESS_TOKEN") or os.environ.get("MAPILLARY_TOKEN")
    INAT_LICENSES = os.environ.get("INAT_LICENSES", "CC0,CC-BY,CC-BY-SA")
    
    
    # Logging settings
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.environ.get(
        "LOG_FORMAT",
        "%(asctime)s | %(levelname)-7s | %(parent_file)s:%(lineno)-3d | %(message)s",
    )
    LOG_DIR = os.environ.get("LOG_DIR", "logs")
    LOG_FILE = os.environ.get("LOG_FILE", "app.log")
    LOG_MAX_BYTES = os.environ.get("LOG_MAX_BYTES", 10 * 1024 * 1024)  # 10 MB
    LOG_BACKUP_COUNT = os.environ.get("LOG_BACKUP_COUNT", 5)


class DevelopmentConfig(Config):
    """Enable debug mode and auto‑reload."""

    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Settings for running tests."""

    TESTING = True
    DEBUG = True
    LOG_FILE = os.environ.get("TEST_LOG_FILE", "testing.log")


class ProductionConfig(Config):
    """Production‑ready settings."""

    DEBUG = False
    TESTING = False

# config.py
# -----------------------------------------
# Configuration classes for the Vigil Flask app.
# Loaded by the app factory in app/__init__.py via create_app(config_name).
#
# Usage:
#   from config import config
#   app.config.from_object(config["development"])

import os


class Config:
    """
    Base configuration shared by all environments.
    All values are read from environment variables so nothing
    sensitive is ever hard-coded in source control.
    """

    # ------------------------------------------------------------------
    # Flask core
    # ------------------------------------------------------------------
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # ------------------------------------------------------------------
    # Auth settings
    # ------------------------------------------------------------------
    # How long a magic-link token stays valid (minutes)
    MAGIC_LINK_TTL_MINUTES: int = int(os.getenv("MAGIC_LINK_TTL_MINUTES", 15))
    # How long a logged-in session stays valid (hours)
    SESSION_TTL_HOURS: int = int(os.getenv("SESSION_TTL_HOURS", 72))
    # Base URL of the React frontend — used for post-verify redirect
    FRONTEND_BASE_URL: str = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
    # Base URL of this Flask backend — used to build the email magic link
    BACKEND_BASE_URL: str = os.getenv("BACKEND_BASE_URL", "http://localhost:5000")

    # ------------------------------------------------------------------
    # Run system
    # ------------------------------------------------------------------
    MAX_QUERIES_PER_RUN: int = int(os.getenv("MAX_QUERIES_PER_RUN", 100))
    # True = use Python threads for background runs (dev/simple deploys)
    # False = jobs must be dispatched externally (Celery, RQ, etc.)
    ENABLE_THREAD_EXECUTOR: bool = True

    # ------------------------------------------------------------------
    # LLM API keys
    # ------------------------------------------------------------------
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")


class DevelopmentConfig(Config):
    """
    Local development — SQLite, debug mode, hot-reload.
    """

    DEBUG: bool = True
    # SQLite file auto-created at server/instance/vigil_dev.db
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", "sqlite:///vigil_dev.db")


class ProductionConfig(Config):
    """
    Production — PostgreSQL, no debug output.
    Set DATABASE_URL env var to your Postgres connection string.
    """

    DEBUG: bool = False
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", "")


class TestingConfig(Config):
    """
    Automated tests — in-memory SQLite, minimal TTLs for speed.
    """

    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    # Short TTLs so expiry tests run quickly
    MAGIC_LINK_TTL_MINUTES: int = 1
    SESSION_TTL_HOURS: int = 1
    # Skip real email dispatch in tests
    ENABLE_THREAD_EXECUTOR: bool = False


# Registry — looked up by name in create_app(config_name)
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
#
# IMPORTS NEEDED:
#   import os
#
# CLASSES TO DEFINE:
#
#   class Config:
#       - BASE class shared by all environments
#       - SECRET_KEY: read from env var "SECRET_KEY", fallback to "dev-secret-change-in-prod"
#       - SQLALCHEMY_TRACK_MODIFICATIONS: set to False (suppresses warning, saves memory)
#       - MAGIC_LINK_TTL_MINUTES: int (default 15)
#       - SESSION_TTL_HOURS: int (default 72)
#       - FRONTEND_BASE_URL: used in magic-link email URL generation
#       - SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD for email delivery
#       - MAX_QUERIES_PER_RUN: upper cap for manual run request size
#       - ENABLE_THREAD_EXECUTOR: True in dev, can be False in worker-only deploys
#
#   class DevelopmentConfig(Config):
#       - Inherits from Config
#       - DEBUG: True
#       - SQLALCHEMY_DATABASE_URI: "sqlite:///vigil.db"
#         (SQLite file created at instance/vigil.db automatically by Flask)
#
#   class ProductionConfig(Config):
#       - Inherits from Config
#       - DEBUG: False
#       - SQLALCHEMY_DATABASE_URI: read from env var "DATABASE_URL"
#         (Swap to Postgres in prod: "postgresql://user:pass@host/vigil")
#
#   class TestingConfig(Config):
#       - Inherits from Config
#       - TESTING: True
#       - SQLALCHEMY_DATABASE_URI: "sqlite:///:memory:"
#         (In-memory SQLite — fast, isolated, disposable for tests)
#
# CONFIG REGISTRY (dict):
#   config = {
#       "development": DevelopmentConfig,
#       "production": ProductionConfig,
#       "testing": TestingConfig,
#       "default": DevelopmentConfig
#   }
#   This dict is imported by create_app() to look up the right config class by name.
#   Usage: app.config.from_object(config[config_name])

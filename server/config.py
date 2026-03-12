# config.py
# -----------------------------------------
# Configuration classes for the Vigil Flask app.
# Loaded by the app factory in app/__init__.py via create_app(config_name).
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

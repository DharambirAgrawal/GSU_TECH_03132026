# app/__init__.py
# -----------------------------------------
# Application factory for Vigil Flask app.
# All initialization happens inside create_app() so multiple
# instances can coexist (useful for testing with different configs).
#
# IMPORTS NEEDED:
#   from flask import Flask
#   from flask_cors import CORS
#   from .extensions import db, migrate
#   from config import config
#
# FUNCTION: create_app(config_name="default") -> Flask app
#
#   STEP 1 — Create Flask instance:
#       app = Flask(__name__, instance_relative_config=True)
#       app.config.from_object(config[config_name])
#
#   STEP 2 — Initialize extensions with the app:
#       db.init_app(app)
#       migrate.init_app(app, db)
#       CORS(app)  — allow cross-origin requests from the React frontend
#
#   STEP 3 — Import ALL models so Flask-Migrate can discover them for migrations.
#       If you skip importing a model here, flask db migrate won't see it.
#       Import every module from app/models/:
#           from .models import company, auth, run_history, query, accuracy, crawl, content, competitor, source, ethics
#
#   STEP 4 — Register all blueprints with URL prefixes:
#       dashboard_bp    → /api/dashboard
#       visibility_bp   → /api/visibility
#       accuracy_bp     → /api/accuracy
#       competitors_bp  → /api/competitors
#       actions_bp      → /api/actions
#       crawl_bp        → /api/crawl
#       query_bp        → /api/query
#       auth_bp         → /api/auth
#       runs_bp         → /api/runs
#       history_bp      → /api/history
#       ethics_bp       → /api/ethics
#
#   STEP 5 — Manual background task model (NO scheduler):
#       - Work is triggered only when authenticated user clicks Start in frontend.
#       - Trigger endpoints create run records with status=queued.
#       - A lightweight async executor/thread worker picks queued runs.
#       - No daily/weekly global automation is configured in app startup.
#
#   STEP 6 — Return the configured app instance
#       return app
#
# NOTE:
#   Do NOT import models at the top of this file — only inside create_app()
#   to avoid circular import issues (models import db from extensions.py).

# app/__init__.py
# -----------------------------------------
# Application factory for Vigil Flask app.
# All initialization happens inside create_app() so multiple
# instances can coexist (useful for testing with different configs).
#
# IMPORTS NEEDED:
#   from flask import Flask
#   from flask_cors import CORS
#   from .extensions import db, migrate, scheduler
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
#           from .models import company, query, accuracy, crawl, content, competitor, source, ethics
#
#   STEP 4 — Register all blueprints with URL prefixes:
#       dashboard_bp    → /api/dashboard
#       visibility_bp   → /api/visibility
#       accuracy_bp     → /api/accuracy
#       competitors_bp  → /api/competitors
#       actions_bp      → /api/actions
#       crawl_bp        → /api/crawl
#       query_tester_bp → /api/query
#       ethics_bp       → /api/ethics        (for EthicsFlag endpoints)
#
#   STEP 5 — Register background jobs with APScheduler:
#       Import job functions from app/jobs/:
#           from .jobs.daily_queries import run_daily_queries
#           from .jobs.weekly_crawl import run_weekly_crawl
#           from .jobs.score_updater import run_score_updater
#       Add jobs:
#           scheduler.add_job(run_daily_queries, "interval", hours=24, id="daily_queries")
#           scheduler.add_job(run_weekly_crawl,  "interval", weeks=1,  id="weekly_crawl")
#       Start scheduler only if not already running:
#           if not scheduler.running: scheduler.start()
#
#   STEP 6 — Return the configured app instance
#       return app
#
# NOTE:
#   Do NOT import models at the top of this file — only inside create_app()
#   to avoid circular import issues (models import db from extensions.py).

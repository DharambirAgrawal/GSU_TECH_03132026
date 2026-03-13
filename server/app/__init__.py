# app/__init__.py
# -----------------------------------------
# Application factory for the Vigil Flask backend.
#
# create_app() is called by:
#   - run.py   (dev/prod server startup)
#   - tests    (with config_name="testing")
#
# Nothing at module level touches the DB or config —
# everything lives inside create_app() to allow multiple
# isolated instances (essential for testing).

from flask import Flask
from flask_cors import CORS

from config import config


def create_app(config_name: str = "default") -> Flask:
    """
    Build and return a fully configured Flask application.

    Args:
        config_name: One of "development", "production", "testing", "default".
                     Maps to a Config class in config.py.

    Returns:
        Configured Flask app instance.
    """

    # ------------------------------------------------------------------
    # Step 1 — Create Flask instance
    # ------------------------------------------------------------------
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    # ------------------------------------------------------------------
    # Step 2 — Bind extensions to the app
    # ------------------------------------------------------------------
    from .extensions import db, migrate

    db.init_app(app)
    migrate.init_app(app, db)

    # Allow cross-origin requests from the React frontend
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ------------------------------------------------------------------
    # Step 3 — Import model modules so Flask-Migrate discovers tables.
    # ------------------------------------------------------------------
    with app.app_context():
        from .models import auth, company, simulation  # noqa: F401

        # Dev convenience mode:
        # - AUTO_CREATE_SCHEMA_ON_STARTUP: create missing tables automatically.
        # - RESET_DB_ON_STARTUP: drop and recreate all tables for a fresh local DB.
        if app.config.get("RESET_DB_ON_STARTUP"):
            db.drop_all()
            db.create_all()
        elif app.config.get("AUTO_CREATE_SCHEMA_ON_STARTUP"):
            db.create_all()

        # --------------------------------------------------------------
        # Step 4 — Register active blueprints.
        # --------------------------------------------------------------
        from .routes.auth import bp as auth_bp
        from .routes.simulations import bp as simulations_bp

        app.register_blueprint(auth_bp, url_prefix="/api/auth")
        app.register_blueprint(simulations_bp, rl_prefix="/api/agent")

        # --------------------------------------------------------------
        # Step 5 — Health-check route (no auth needed)
        # --------------------------------------------------------------
        @app.route("/api/health")
        def health():
            from flask import jsonify

            return jsonify({"status": "ok", "env": config_name}), 200

    return app


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

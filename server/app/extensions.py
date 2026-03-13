# app/extensions.py
# -----------------------------------------
# Single shared instances of Flask extensions.
#
# These are created at module level so models can do:
#   from app.extensions import db
# without causing circular imports.
#
# The actual Flask app is bound later in create_app() via:
#   db.init_app(app)
#   migrate.init_app(app, db)

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# ORM instance — all models inherit from db.Model
db = SQLAlchemy()

# Database migration manager (Alembic wrapper)
# CLI: flask db init / flask db migrate / flask db upgrade
migrate = Migrate()
#
# IMPORTS NEEDED:
#   from flask_sqlalchemy import SQLAlchemy
#   from flask_migrate import Migrate
#
# IMPORTANT DESIGN NOTE:
#   This backend no longer uses scheduler-driven app-wide automation.
#   All crawl/query work is triggered manually by authenticated users
#   from the frontend and then executed as asynchronous background tasks
#   scoped to a single company run request.
#
# INSTANCES TO CREATE:
#
#   db = SQLAlchemy()
#       - The ORM instance. All models import this to define db.Column, db.Model, etc.
#       - Bound to app in create_app() via db.init_app(app)
#
#   migrate = Migrate()
#       - Handles `flask db init`, `flask db migrate`, `flask db upgrade`
#       - Bound to app in create_app() via migrate.init_app(app, db)
#
# USAGE PATTERN (in any model file):
#   from app.extensions import db
#   class MyModel(db.Model): ...

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()

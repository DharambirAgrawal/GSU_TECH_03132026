# app/extensions.py
# -----------------------------------------
# Single shared instances of Flask extensions.
# These are created HERE (not inside the app factory) so that
# models can import `db` without causing circular imports.
# The actual app is bound to them later via db.init_app(app) in create_app().
#
# IMPORTS NEEDED:
#   from flask_sqlalchemy import SQLAlchemy
#   from flask_migrate import Migrate
#   from apscheduler.schedulers.background import BackgroundScheduler
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
#   scheduler = BackgroundScheduler()
#       - APScheduler instance used for background jobs (24hr queries, weekly crawls)
#       - Jobs are registered in create_app() after blueprints are loaded
#       - scheduler.start() is called in create_app() to begin background execution
#
# USAGE PATTERN (in any model file):
#   from app.extensions import db
#   class MyModel(db.Model): ...

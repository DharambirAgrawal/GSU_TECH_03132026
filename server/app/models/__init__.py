# app/models/__init__.py
# -----------------------------------------
# Imports all model modules so that Flask-Migrate (Alembic) can discover
# every table when running `flask db migrate`.
# If a model module is NOT imported here, its table will be invisible to migrations.
#
# IMPORTS NEEDED (import each module, not just the classes):
#   from . import company
#   from . import query
#   from . import accuracy
#   from . import crawl
#   from . import content
#   from . import competitor
#   from . import source
#   from . import ethics
#
# No other logic in this file — just imports.

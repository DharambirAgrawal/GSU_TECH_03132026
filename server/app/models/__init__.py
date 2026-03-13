# app/models/__init__.py
# -----------------------------------------
# Import every model module here.
# Flask-Migrate (Alembic) discovers tables by scanning imported models,
# so any module not listed here will be missed by `flask db migrate`.

from . import (
    accuracy,
    auth,
    company,
    competitor,
    content,
    crawl,
    ethics,
    query,
    run_history,
    source,
)
#
# IMPORTS NEEDED (import each module, not just the classes):
#   from . import company
#   from . import auth
#   from . import query
#   from . import run_history
#   from . import accuracy
#   from . import crawl
#   from . import content
#   from . import competitor
#   from . import source
#   from . import ethics
#
# No other logic in this file — just imports.

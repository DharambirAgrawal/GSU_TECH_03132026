# app/routes/__init__.py
# -----------------------------------------
# Route package index.
#
# Active backend route groups:
#   - auth.py         -> company registration + magic-link authentication
#   - queries.py      -> query prompt generation and retrieval
#   - simulations.py  -> simulation start endpoint (Celery trigger)
#
# Routes expose `bp` blueprints and are registered in app/__init__.py.

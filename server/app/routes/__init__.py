# app/routes/__init__.py
# -----------------------------------------
# Route package index.
#
# Active backend route groups:
#   - auth.py         -> registration + domain magic-link login
#   - runs.py         -> generate/edit/start manual runs + status polling
#   - query_tester.py -> low-level simulate/template endpoints
#   - dashboard.py    -> overview and score cards
#   - visibility.py   -> mention/source visibility analytics
#   - accuracy.py     -> fact-check and error analytics
#   - competitors.py  -> competitor rankings and gaps
#   - actions.py      -> generated content-fix queue
#   - crawl.py        -> manual crawl and readability audit
#   - ethics.py       -> compliance and risk flags
#
# All files expose `bp` Blueprints and are registered in app/__init__.py.

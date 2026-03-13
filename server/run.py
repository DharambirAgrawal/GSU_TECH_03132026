# run.py
# -----------------------------------------
# Entry point for the Vigil Flask application.
#
# Development:
#   python run.py
#
# Production (gunicorn):
#   gunicorn "app:create_app('production')" --bind 0.0.0.0:5000 --workers 4

import os

from app import create_app

# Read FLASK_ENV from environment; default to development
env = os.getenv("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))
    # debug=True enables auto-reload on code changes (dev only)
    app.run(host=host, port=port, debug=(env == "development"), use_reloader=True)
#
# IMPORTS NEEDED:
#   from app import create_app        # The app factory function
#   import os                         # To read PORT env var if needed
#
# WHAT TO DO:
#   1. Call create_app("development") to get the configured Flask app instance.
#      Pass "production" when deploying via env var APP_ENV=production.
#
#   2. Optionally read HOST and PORT from environment variables so the
#      server bind address can be configured without code changes.
#      Defaults: host="0.0.0.0", port=5000
#
#   3. Run under: if __name__ == "__main__": app.run(...)
#      - debug=True in development so code changes auto-reload
#      - use_reloader=True allows Flask to reload on file save
#
# NOTE:
#   In production, do NOT use app.run() directly.
#   Use a production WSGI server like gunicorn:
#       gunicorn "app:create_app('production')" --bind 0.0.0.0:5000

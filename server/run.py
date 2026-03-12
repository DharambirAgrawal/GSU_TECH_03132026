# run.py
# -----------------------------------------
# Entry point for the Vigil Flask application.
# Run this file directly with: python run.py
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

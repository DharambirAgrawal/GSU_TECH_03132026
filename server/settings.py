# settings.py
# -----------------------------------------
# Module-level settings loaded from the .env file.
# Used by services that run outside the Flask app context
# (e.g. emailing.py which may be called from background threads).
#
# For settings used inside Flask routes, prefer current_app.config.

import os

from dotenv import load_dotenv

load_dotenv()

POWERAUTOMATE_EMAIL_API_URL = os.getenv("POWERAUTOMATE_EMAIL_API_URL")

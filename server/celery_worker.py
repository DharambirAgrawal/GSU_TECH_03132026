from __future__ import annotations

import os

from app import create_app
from app.celery_app import celery_app, init_celery

flask_app = create_app(os.getenv("FLASK_ENV", "development"))
init_celery(flask_app)

import app.tasks.simulations  # noqa: F401,E402

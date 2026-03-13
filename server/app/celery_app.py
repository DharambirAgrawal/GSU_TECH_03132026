from __future__ import annotations

from celery import Celery, Task

celery_app = Celery("vigil")


def init_celery(app) -> Celery:
    celery_app.conf.update(app.config.get("CELERY", {}))

    class FlaskTask(Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = FlaskTask
    app.extensions["celery"] = celery_app
    return celery_app

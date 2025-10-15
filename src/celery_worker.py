from typing import Any

from celery import Celery
from celery.schedules import crontab

from celery_conf import celery_app
from src.tasks import task_for_clean_tokens


@celery_app.on_after_configure.connect
def setup_periodic_task(sender: Celery, **kwargs: Any) -> None:
    sender.add_periodic_task(
        crontab(hour=9, minute=0),
        task_for_clean_tokens.s(),
        name="Delete expired token"
    )

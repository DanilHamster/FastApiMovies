from celery.schedules import crontab

from celery_conf import celery_app

from src.tasks import task_for_clean_tokens


"""Example"""


@celery_app.on_after_configure.connect
def setup_periodic_task(sender, **kwargs):
    sender.add_periodic_task(
        30.0,
        task_for_clean_tokens.s(),
        name="Test"
    )
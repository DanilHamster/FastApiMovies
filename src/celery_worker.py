import os

from celery import Celery

from celery.schedules import crontab


celery_app = Celery(
    "worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

celery_app.conf.timezone = "Europe/Kiev"

celery_app.autodiscover_tasks()


"""Example"""
# @celery_app.on_after_configure.connect
# def setup_periodic_task(sender, **kwargs):
#     from src.tasks import notify_user
#     sender.add_periodic_task(
#         10.0,
#         notify_user.s(),
#         name="Test"
#     )

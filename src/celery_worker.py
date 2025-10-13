from celery_conf import celery_app
from celery.schedules import crontab
# from src.tasks import notify_user

# """Example"""
# @celery_app.on_after_configure.connect
# def setup_periodic_task(sender, **kwargs):
#     sender.add_periodic_task(
#         10.0,
#         notify_user.s(),
#         name="Test"
#     )

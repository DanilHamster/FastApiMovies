from celery_conf import celery_app

"""Example"""
@celery_app.task(name="notify")
def notify_user():
    print("🔔 Notify")


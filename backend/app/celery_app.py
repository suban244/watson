from celery import Celery

from celery.schedules import crontab
from config import settings
from celery.signals import worker_init, beat_init
import logfire


@worker_init.connect()
def init_worker(*args, **kwargs):
    logfire.configure(service_name="worker")
    logfire.instrument_celery()


@beat_init.connect()
def init_beat(*args, **kwargs):
    logfire.configure(service_name="beat")
    logfire.instrument_celery()


celery_app = Celery(__name__)
celery_app.conf.broker_url = settings.CELERY_BROKER_URL
celery_app.conf.result_backend = settings.CELERY_RESULT_BACKEND

celery_app.autodiscover_tasks(["tasks"])
# tasks included explicitly via Celery(include=["tasks"])

celery_app.conf.beat_schedule = {
    "add-every-minute": {
        "task": "tasks.add.add",
        "schedule": crontab(minute="*/1"),
        "args": (16, 16),
    },
    "calculate-expenses-of-last-week": {
        "task": "tasks.finances.calculate_expenses_of_last_week",
        "schedule": crontab(hour=8, minute=0, day_of_week="mon"),
    },
}

celery_app.conf.timezone = "Asia/Kathmandu"  # type: ignore

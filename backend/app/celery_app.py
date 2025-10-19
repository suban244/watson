from celery import Celery

# from celery.schedules import crontab
from config import settings

celery_app = Celery(__name__)
celery_app.conf.broker_url = settings.CELERY_BROKER_URL
celery_app.conf.result_backend = settings.CELERY_RESULT_BACKEND

celery_app.autodiscover_tasks(["tasks"])
# tasks included explicitly via Celery(include=["tasks"])

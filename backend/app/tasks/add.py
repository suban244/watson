from celery_app import celery_app


@celery_app.task
def add(x: int, y: int):
    return x + y

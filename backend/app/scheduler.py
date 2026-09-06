from taskiq import TaskiqScheduler
from taskiq_redis import RedisScheduleSource

from config import settings
from taskiq_app import broker

source = RedisScheduleSource(settings.REDIS_URL)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[source],
)

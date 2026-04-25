from taskiq import TaskiqScheduler
from taskiq_redis import RedisScheduleSource
from taskiq_app import broker
from config import settings

source = RedisScheduleSource(settings.REDIS_URL)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[source],
)

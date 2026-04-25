import redis
from config import settings
# from redis.asyncio.client import Redis


class RedisService:
    def __init__(self):
        self.client = redis.StrictRedis.from_url(settings.REDIS_URL)


redis_service = RedisService()

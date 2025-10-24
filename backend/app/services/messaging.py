from services.redis import redis_service
import json


class MessagingService:
    """Helps send messages through discord via Redis Pub/Sub."""

    def __init__(self):
        pass

    def send_message(self, message: dict | str, channel: str = "default"):
        redis_service.client.publish(channel, json.dumps(message))


messaging_service = MessagingService()

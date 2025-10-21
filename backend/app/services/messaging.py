from services.redis import redis_service


class MessagingService:
    """Helps send messages through discord via Redis Pub/Sub."""

    def __init__(self):
        pass

    def send_message(self, message: str, channel: str = "default"):
        redis_service.client.publish(channel, message)


messaging_service = MessagingService()

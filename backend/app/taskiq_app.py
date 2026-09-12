from taskiq import TaskiqEvents, TaskiqState
from taskiq.middlewares.opentelemetry_middleware import OpenTelemetryMiddleware
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from config import settings
from observability import setup_logfire

broker = (
    RedisStreamBroker(settings.REDIS_URL)
    .with_result_backend(
        RedisAsyncResultBackend(settings.REDIS_URL, result_ex_time=1000)
    )
    .with_middlewares(OpenTelemetryMiddleware())
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_worker_startup(state: TaskiqState) -> None:
    setup_logfire("worker")

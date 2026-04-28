from taskiq import TaskiqEvents, TaskiqState
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker
from config import settings
import logfire

broker = RedisStreamBroker(settings.REDIS_URL).with_result_backend(
    RedisAsyncResultBackend(settings.REDIS_URL, result_ex_time=1000)
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def on_worker_startup(state: TaskiqState) -> None:
    logfire.configure(
        service_name="worker",
        token=settings.LOGFIRE_TOKEN,
        send_to_logfire="if-token-present",
        environment=settings.APP_ENV,
        scrubbing=False,
        distributed_tracing=True,
    )

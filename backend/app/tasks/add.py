from taskiq_app import broker
import logfire


@broker.task
@logfire.instrument
def add(x: int, y: int):
    return x + y

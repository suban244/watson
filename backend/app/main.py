from services.messaging import messaging_service
import logfire
from config import settings
from fastapi import FastAPI
from api import router as api_router
from tasks import add

app = FastAPI()
logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    send_to_logfire="if-token-present",
    environment=settings.APP_ENV,
    scrubbing=False,
    service_name="web-server",
    distributed_tracing=True,
)

logfire.instrument_fastapi(app, capture_headers=True)


@app.get("/")
def read_root():
    return {"Hello": "Welcome To Watson"}


@app.get("/health/")
def health():
    return {"status": "ok"}


@app.get("/tasks/")
def task():
    add.delay(4, 6)  # type: ignore
    messaging_service.send_message("New task added: add(4, 6)", channel="default")
    return {"status": "Task added"}


app.include_router(api_router, prefix="/api/v1")

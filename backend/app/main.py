import logfire
from config import settings
from fastapi import FastAPI
from api import router as api_router

app = FastAPI()
logfire.configure(
    token=settings.LOGFIRE_TOKEN,
    send_to_logfire="if-token-present",
    environment=settings.APP_ENV,
    scrubbing=False,
    service_name="web-server",
)

logfire.instrument_fastapi(app, capture_headers=True)


@app.get("/")
def read_root():
    return {"Hello": "Welcome To Watson"}


app.include_router(api_router, prefix="/api/v1")

import asyncio
from contextlib import asynccontextmanager

import logfire
from fastapi import FastAPI

from api import router as api_router
from observability import setup_logfire


@asynccontextmanager
async def lifespan(app: FastAPI):
    from bot.bot import run as run_discord_bot

    discord_task = asyncio.create_task(run_discord_bot())
    yield
    discord_task.cancel()
    try:
        await discord_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)

setup_logfire("watson")
logfire.instrument_fastapi(app, capture_headers=True)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx()
logfire.instrument_openai()


@app.get("/")
def read_root():
    return {"Hello": "Welcome To Watson"}


@app.get("/health/")
def health():
    return {"status": "ok"}


app.include_router(api_router, prefix="/api/v1")

"""The last few weekly reviews, kept so the next one can avoid repeating them.

A capped Redis list rather than a table: only the newest handful ever matter,
and Redis already runs with appendonly, so they survive a restart.
"""

from datetime import date
from typing import cast

from pydantic import BaseModel
from redis.asyncio.client import Redis

from config import settings

KEY = "weekly_summaries"
KEEP = 4


class PastReview(BaseModel):
    period_start: date
    text: str


def _redis() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def recent() -> list[PastReview]:
    """The stored reviews, newest first."""
    async with _redis() as redis:
        stored = cast(list[str], await redis.lrange(KEY, 0, -1))  # type: ignore[misc]
    return [PastReview.model_validate_json(raw) for raw in stored]


async def remember(review: PastReview) -> None:
    async with _redis() as redis:
        await redis.lpush(KEY, review.model_dump_json())  # type: ignore[misc]
        await redis.ltrim(KEY, 0, KEEP - 1)  # type: ignore[misc]


async def clear() -> None:
    async with _redis() as redis:
        await redis.delete(KEY)

from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager

from sqlalchemy.engine import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from .engine import build_connection_string

ASYNC_DATABASE_URL = build_connection_string(is_async=True)
SYNC_DATABASE_URL = build_connection_string()

# Small pools: single-user app on a Raspberry Pi, keep Postgres memory low.
POOL_OPTIONS = dict(pool_size=5, max_overflow=5, pool_recycle=3600, pool_timeout=60)

engine: AsyncEngine = create_async_engine(ASYNC_DATABASE_URL, **POOL_OPTIONS)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

# Only the taskiq worker uses sync sessions; create the engine lazily so the
# API/bot process never opens a second connection pool.
_sync_session_maker: sessionmaker[Session] | None = None


def _get_sync_session_maker() -> sessionmaker[Session]:
    global _sync_session_maker
    if _sync_session_maker is None:
        _sync_session_maker = sessionmaker(
            create_engine(SYNC_DATABASE_URL, **POOL_OPTIONS)
        )
    return _sync_session_maker


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session


@contextmanager
def sync_session_manager() -> Generator[Session]:
    session = _get_sync_session_maker()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

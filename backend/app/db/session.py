from contextlib import contextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .engine import build_connection_string
from sqlalchemy.ext.asyncio import AsyncSession
from collections.abc import AsyncGenerator
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import sessionmaker, Session
from collections.abc import Generator

ASYNC_DATABASE_URL = build_connection_string(is_async=True)
SYNC_DATABASE_URL = build_connection_string()

engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=20,
    max_overflow=20,
    pool_recycle=3600,
    pool_timeout=60,
)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


sync_engine = create_engine(
    SYNC_DATABASE_URL,
    pool_size=20,
    max_overflow=20,
    pool_recycle=3600,
    pool_timeout=60,
)
sync_session_maker = sessionmaker(sync_engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a database session with tenant isolation.

    Yields:
        AsyncSession: Database session with tenant context

    Raises:
        SQLAlchemyError: For database-related errors
        ValueError: If tenant ID is invalid
    """
    async with async_session_maker() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            print(f"Database session error: {e}")
            await session.rollback()
            raise
        except ValueError as e:
            print(f"Invalid tenant ID: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error in session: {e}")
            await session.rollback()
            raise


@contextmanager
def sync_session_manager() -> Generator[Session, None, None]:
    session = sync_session_maker()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        raise

from config import settings

SYNC_DB_API = "psycopg"
ASYNC_DB_API = "asyncpg"

def build_connection_string(
    db_api: str = ASYNC_DB_API,
    user: str = settings.POSTGRES_USER,
    password: str = settings.POSTGRES_PASSWORD,
    host: str = settings.POSTGRES_HOST,
    port: int = settings.POSTGRES_PORT,
    db: str = settings.POSTGRES_DB,
) -> str:
    return f"postgresql+{db_api}://{user}:{password}@{host}:{port}/{db}"

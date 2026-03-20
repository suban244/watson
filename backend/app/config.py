from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    APP_ENV: Literal["local", "prod"] = "local"
    PROJECT_NAME: str = "Watson"

    # Postgres settings
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = ""

    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    LOGFIRE_TOKEN: str | None = None
    INTERNAL_API_TOKEN: str


settings = Settings()  # type: ignore

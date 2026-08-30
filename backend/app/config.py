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

    # SELECT-only login for model-generated analysis SQL; see db.readonly.
    POSTGRES_READONLY_USER: str = "watson_ro"
    POSTGRES_READONLY_PASSWORD: str = "watson_ro_local"

    REDIS_URL: str

    LOGFIRE_TOKEN: str | None = None
    INTERNAL_API_TOKEN: str

    # Discord bot
    DISCORD_TOKEN: str = ""
    SOURCE_CHANNEL_ID: str = ""

    # AI providers
    MISTRAL_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # Prabin Spotify invoice email task
    EXTERNAL_PRABIN_EMAIL_SMTP_SERVER: str = "smtp.gmail.com"
    EXTERNAL_PRABIN_EMAIL_SMTP_PORT: int = 587
    EXTERNAL_PRABIN_EMAIL_SENDER: str = ""
    EXTERNAL_PRABIN_EMAIL_PASSWORD: str = ""
    EXTERNAL_PRABIN_EMAIL_SENDER_NAME: str = "Invoice Sender"


settings = Settings()  # type: ignore

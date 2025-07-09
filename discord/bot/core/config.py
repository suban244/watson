from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    APP_ENV: Literal["local", "prod"] = "local"
    PROJECT_NAME: str = "Watson"

    DISCORD_TOKEN: str
    SOURCE_CHANNEL_ID: str

    # Postgres settings
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = ""

    MISTRAL_API_KEY: str

    EXPENSE_SHEETS_CREDENTIALS_PATH: str
    EXPENSE_SHEET_NAME: str

    LOGFIRE_TOKEN: str

    class Config:
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore

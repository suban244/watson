from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    app_env: Literal["local", "prod"] = "local"
    project_name: str = "Watson"

    # Postgres settings
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_HOST: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = ""


settings = Settings()

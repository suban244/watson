from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DISCORD_TOKEN: str
    SOURCE_CHANNEL_ID: str

    MISTRAL_API_KEY: str

    EXPENSE_SHEETS_CREDENTIALS_PATH: str
    EXPENSE_SHEET_NAME: str

    LOGFIRE_TOKEN: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # type: ignore

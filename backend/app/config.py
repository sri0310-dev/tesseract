from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Hectar Commodity Flow Intelligence"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Eximpedia API
    EXIMPEDIA_BASE_URL: str = "https://web.eximpedia.app/backend/apis/v1"
    EXIMPEDIA_CLIENT_ID: str = ""
    EXIMPEDIA_CLIENT_SECRET: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost:5432/hectar"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # API settings
    API_MAX_CONCURRENT_REQUESTS: int = 5
    API_MIN_REQUEST_INTERVAL: float = 1.0
    API_PAGE_SIZE: int = 1000

    # Token settings
    TOKEN_REFRESH_BUFFER_SECONDS: int = 300

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

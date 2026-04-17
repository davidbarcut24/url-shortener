from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener"
    REDIS_URL: str = "redis://localhost:6379"
    BASE_URL: str = "http://localhost:8000"
    SHORT_CODE_LENGTH: int = 7
    DEFAULT_CACHE_TTL: int = 86400  # 24h
    RATE_LIMIT_SHORTEN: int = 10    # requests per window
    RATE_LIMIT_REDIRECT: int = 60
    RATE_LIMIT_WINDOW: int = 60     # seconds

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

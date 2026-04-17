import warnings

from pydantic_settings import BaseSettings, SettingsConfigDict

# Sentinel used to detect when IP_HASH_SALT was never set by the operator.
_UNSET_SALT = "CHANGE_ME_IN_PRODUCTION"


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener"
    REDIS_URL: str = "redis://localhost:6379"
    BASE_URL: str = "http://localhost:8000"
    # Comma-separated list of allowed CORS origins, e.g.
    # ALLOWED_ORIGINS=http://localhost:5173,https://example.com
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    SHORT_CODE_LENGTH: int = 7
    DEFAULT_CACHE_TTL: int = 86400  # 24h
    RATE_LIMIT_SHORTEN: int = 10    # requests per window
    RATE_LIMIT_REDIRECT: int = 60
    RATE_LIMIT_WINDOW: int = 60     # seconds
    # Secret used to HMAC-hash visitor IPs before storage.
    # MUST be set to a random value in production (e.g. openssl rand -hex 32).
    # Leaving this at the default renders all IP hashes insecure.
    IP_HASH_SALT: str = _UNSET_SALT

    # SQLAlchemy async engine connection pool settings.
    # pool_size + max_overflow = total max simultaneous DB connections.
    # Default of 5 + 10 = 15 matches Supabase/Neon free-tier connection limits.
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

if settings.IP_HASH_SALT == _UNSET_SALT:
    warnings.warn(
        "IP_HASH_SALT is set to the default placeholder value. "
        "Set a strong random secret via the IP_HASH_SALT environment variable "
        "before deploying to production (e.g. openssl rand -hex 32).",
        stacklevel=1,
    )

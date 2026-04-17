from datetime import datetime, timezone
from app.config import settings
from app.models import Url


def _compute_ttl(expires_at: datetime | None) -> int:
    if expires_at is None:
        return settings.DEFAULT_CACHE_TTL
    remaining = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    return max(1, min(remaining, settings.DEFAULT_CACHE_TTL))


async def get_cached_url(redis, short_code: str) -> str | None:
    return await redis.get(f"url:{short_code}")


async def cache_url(redis, url: Url) -> None:
    ttl = _compute_ttl(url.expires_at)
    await redis.setex(f"url:{url.short_code}", ttl, url.original_url)

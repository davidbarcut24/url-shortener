import re
import redis.asyncio as aioredis
from sqlalchemy import update
from app.db.session import AsyncSessionLocal
from app.models import Url
from app.cache import pool
from app.config import settings

_SHORT_CODE_RE = re.compile(r"^[A-Za-z0-9]{1,10}$")

# Maximum TTL for a buffered click counter.  Set it to double the default
# cache TTL so the key cannot outlive the URL it belongs to by much.
_BUFFER_TTL = settings.DEFAULT_CACHE_TTL * 2


async def buffer_click(redis, short_code: str) -> None:
    key = f"clicks:buffer:{short_code}"
    pipe = redis.pipeline()
    await pipe.incr(key)
    # Only set the TTL when the counter is first created (NX flag) so we
    # don't keep pushing the expiry forward on every click.
    await pipe.expire(key, _BUFFER_TTL, nx=True)
    await pipe.execute()


async def flush_click_counts() -> None:
    # Re-use the module-level connection pool instead of opening a new
    # connection on every scheduler tick.
    redis = aioredis.Redis(connection_pool=pool)
    try:
        cursor = 0
        keys: list[str] = []
        # SCAN iterates the keyspace in O(1) chunks; safe for production use
        # unlike KEYS which blocks the server for the full scan.
        while True:
            cursor, batch = await redis.scan(cursor, match="clicks:buffer:*", count=100)
            keys.extend(batch)
            if cursor == 0:
                break

        if not keys:
            return

        async with AsyncSessionLocal() as db:
            for key in keys:
                count = await redis.getdel(key)
                if count and int(count) > 0:
                    # The key format is "clicks:buffer:<short_code>".
                    # Validate the extracted token before using it in a query
                    # to guard against unexpected key shapes in Redis.
                    short_code = key.split(":")[-1]
                    if not _SHORT_CODE_RE.match(short_code):
                        continue
                    await db.execute(
                        update(Url)
                        .where(Url.short_code == short_code)
                        .values(click_count=Url.click_count + int(count))
                    )
            await db.commit()
    finally:
        await redis.aclose()

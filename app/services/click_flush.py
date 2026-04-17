from sqlalchemy import update
from app.db.session import AsyncSessionLocal
from app.models import Url
from app.cache import get_redis


async def buffer_click(redis, short_code: str) -> None:
    await redis.incr(f"clicks:buffer:{short_code}")


async def flush_click_counts() -> None:
    redis_gen = get_redis()
    redis = await redis_gen.__anext__()
    try:
        keys = await redis.keys("clicks:buffer:*")
        if not keys:
            return

        async with AsyncSessionLocal() as db:
            for key in keys:
                count = await redis.getdel(key)
                if count and int(count) > 0:
                    short_code = key.split(":")[-1]
                    await db.execute(
                        update(Url)
                        .where(Url.short_code == short_code)
                        .values(click_count=Url.click_count + int(count))
                    )
            await db.commit()
    finally:
        await redis.aclose()

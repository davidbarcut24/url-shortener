async def check_rate_limit(redis, key: str, limit: int, window: int) -> bool:
    pipe = redis.pipeline()
    await pipe.incr(key)
    await pipe.expire(key, window)
    results = await pipe.execute()
    return results[0] <= limit

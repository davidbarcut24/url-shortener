# Lua script for atomic rate limiting.
# INCR returns the new count; EXPIRE is only set when the key is brand-new
# (count == 1), so the window never resets mid-flight on a busy key.
_RATE_LIMIT_LUA = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


async def check_rate_limit(redis, key: str, limit: int, window: int) -> bool:
    count = await redis.eval(_RATE_LIMIT_LUA, 1, key, window)
    return int(count) <= limit

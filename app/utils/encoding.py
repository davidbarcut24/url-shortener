import hashlib
import time

BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _to_base62(num: int) -> str:
    if num == 0:
        return BASE62[0]
    result = []
    while num:
        result.append(BASE62[num % 62])
        num //= 62
    return "".join(reversed(result))


def generate_short_code(url: str, length: int = 7, attempt: int = 0) -> str:
    seed = f"{url}{time.time_ns()}{attempt}"
    digest = hashlib.sha256(seed.encode()).hexdigest()
    num = int(digest[:16], 16)
    code = _to_base62(num)
    return code[:length].ljust(length, "0")

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.cache import get_redis
from app.services import url_service
from app.services.rate_limiter import check_rate_limit
from app.services.click_flush import buffer_click
from app.services.cache_service import get_cached_url, cache_url
from app.config import settings

router = APIRouter(tags=["redirect"])

# Only alphanumeric short codes up to 10 characters are valid.
_SHORT_CODE_RE = re.compile(r"^[A-Za-z0-9]{1,10}$")


def _is_safe_url(url: str) -> bool:
    """Return True only if the URL uses http or https scheme."""
    return url.startswith(("http://", "https://"))


@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    if not _SHORT_CODE_RE.match(short_code):
        raise HTTPException(status_code=404, detail="Short URL not found.")

    ip = (request.headers.get("X-Forwarded-For") or request.client.host).split(",")[0].strip()
    allowed = await check_rate_limit(
        redis,
        key=f"rate:redirect:{ip}",
        limit=settings.RATE_LIMIT_REDIRECT,
        window=settings.RATE_LIMIT_WINDOW,
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    cached = await get_cached_url(redis, short_code)
    if cached == "__expired__":
        raise HTTPException(status_code=410, detail="This link has expired.")
    if cached:
        # Re-validate the cached URL before trusting it to guard against
        # Redis poisoning attacks.
        if not _is_safe_url(cached):
            raise HTTPException(status_code=500, detail="Stored URL is invalid.")
        await buffer_click(redis, short_code)
        return RedirectResponse(url=cached, status_code=302)

    try:
        url = await url_service.get_url(db, short_code)
    except url_service.NotFoundError:
        raise HTTPException(status_code=404, detail="Short URL not found.")
    except url_service.ExpiredError:
        await redis.setex(f"url:{short_code}", 3600, "__expired__")
        raise HTTPException(status_code=410, detail="This link has expired.")

    await cache_url(redis, url)
    await buffer_click(redis, short_code)

    return RedirectResponse(url=url.original_url, status_code=302)

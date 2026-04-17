from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.cache import get_redis
from app.schemas import ShortenRequest, ShortenResponse
from app.services import url_service
from app.services.rate_limiter import check_rate_limit
from app.config import settings

router = APIRouter(tags=["urls"])


@router.post("/shorten", response_model=ShortenResponse, status_code=201)
async def shorten_url(
    body: ShortenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    ip = (request.headers.get("X-Forwarded-For") or request.client.host).split(",")[0].strip()
    allowed = await check_rate_limit(
        redis,
        key=f"rate:shorten:{ip}",
        limit=settings.RATE_LIMIT_SHORTEN,
        window=settings.RATE_LIMIT_WINDOW,
    )
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")

    try:
        url = await url_service.create_short_url(
            db,
            original_url=body.url,
            expires_in_days=body.expires_in_days,
            custom_code=body.custom_code,
        )
    except url_service.CollisionError:
        # Use a static message so we don't echo back user-supplied values or
        # expose internal retry-exhaustion details.
        detail = (
            "That alias is already taken. Please choose a different one."
            if body.custom_code
            else "Could not generate a unique short code. Please try again."
        )
        raise HTTPException(status_code=409, detail=detail)

    return ShortenResponse(
        short_code=url.short_code,
        short_url=f"{settings.BASE_URL}/{url.short_code}",
        original_url=url.original_url,
        expires_at=url.expires_at,
    )


@router.delete("/url/{short_code}", status_code=204)
async def delete_url(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    try:
        await url_service.delete_url(db, short_code)
    except url_service.NotFoundError:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Atomically replace the cache entry with an __expired__ sentinel so that
    # in-flight requests cannot repopulate the key after the DB row is gone.
    # The sentinel TTL matches the one used for time-based expiry (1 hour),
    # after which the key is dropped and a 404 is returned from the DB.
    pipe = redis.pipeline()
    await pipe.delete(f"url:{short_code}")
    await pipe.setex(f"url:{short_code}", 3600, "__expired__")
    await pipe.execute()

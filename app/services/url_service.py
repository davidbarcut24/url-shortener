from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Url
from app.utils.encoding import generate_short_code
from app.config import settings


MAX_COLLISION_RETRIES = 5


class CollisionError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ExpiredError(Exception):
    pass


async def create_short_url(
    db: AsyncSession,
    original_url: str,
    expires_in_days: int | None = None,
    custom_code: str | None = None,
) -> Url:
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    if custom_code:
        existing = await db.scalar(select(Url).where(Url.short_code == custom_code))
        if existing:
            raise CollisionError(f"Custom code '{custom_code}' already in use")
        short_code = custom_code
    else:
        short_code = await _generate_unique_code(db, original_url)

    url = Url(short_code=short_code, original_url=original_url, expires_at=expires_at)
    db.add(url)
    await db.commit()
    await db.refresh(url)
    return url


async def _generate_unique_code(db: AsyncSession, original_url: str) -> str:
    for attempt in range(MAX_COLLISION_RETRIES):
        code = generate_short_code(original_url, settings.SHORT_CODE_LENGTH, attempt)
        existing = await db.scalar(select(Url).where(Url.short_code == code))
        if not existing:
            return code
    raise CollisionError("Failed to generate unique short code after maximum retries")


async def get_url(db: AsyncSession, short_code: str) -> Url:
    url = await db.scalar(select(Url).where(Url.short_code == short_code))
    if not url:
        raise NotFoundError(short_code)
    # is_active=False means the URL was soft-deleted by the expiry job.
    if not url.is_active:
        raise ExpiredError(short_code)
    if url.expires_at:
        expires = url.expires_at if url.expires_at.tzinfo else url.expires_at.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise ExpiredError(short_code)
    return url


async def get_analytics(db: AsyncSession, short_code: str) -> Url:
    url = await db.scalar(select(Url).where(Url.short_code == short_code))
    if not url:
        raise NotFoundError(short_code)
    return url


async def delete_url(db: AsyncSession, short_code: str) -> None:
    result = await db.execute(delete(Url).where(Url.short_code == short_code))
    await db.commit()
    if result.rowcount == 0:
        raise NotFoundError(short_code)

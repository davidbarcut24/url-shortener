from datetime import datetime, timezone
from sqlalchemy import update
from app.db.session import AsyncSessionLocal
from app.models import Url


async def cleanup_expired_urls() -> int:
    """Mark expired URLs as inactive (soft delete).

    Hard deletion is intentionally avoided so that analytics rows in the
    clicks table are not orphaned and historical data remains queryable.
    The is_active=False flag excludes these rows from all redirect lookups.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(Url)
            .where(
                Url.expires_at.isnot(None),
                Url.expires_at < datetime.now(timezone.utc),
                Url.is_active.is_(True),
            )
            .values(is_active=False)
        )
        await db.commit()
        return result.rowcount

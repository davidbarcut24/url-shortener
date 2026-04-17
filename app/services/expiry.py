from datetime import datetime, timezone
from sqlalchemy import delete
from app.db.session import AsyncSessionLocal
from app.models import Url


async def cleanup_expired_urls() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(Url).where(
                Url.expires_at.isnot(None),
                Url.expires_at < datetime.now(timezone.utc),
            )
        )
        await db.commit()
        return result.rowcount

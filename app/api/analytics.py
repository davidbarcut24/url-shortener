from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.cache import get_redis
from app.schemas import AnalyticsResponse
from app.services import url_service

router = APIRouter(tags=["analytics"])


@router.get("/analytics/{short_code}", response_model=AnalyticsResponse)
async def get_analytics(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    try:
        url = await url_service.get_analytics(db, short_code)
    except url_service.NotFoundError:
        raise HTTPException(status_code=404, detail="Short URL not found.")

    buffered = await redis.get(f"clicks:buffer:{short_code}")
    total_clicks = url.click_count + (int(buffered) if buffered else 0)

    return AnalyticsResponse(
        short_code=url.short_code,
        original_url=url.original_url,
        click_count=total_clicks,
        created_at=url.created_at,
        expires_at=url.expires_at,
    )

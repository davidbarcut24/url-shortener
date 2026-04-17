from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.session import engine
from app.models import Base
from app.api import urls, redirect, analytics
from app.services.click_flush import flush_click_counts
from app.services.expiry import cleanup_expired_urls


scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scheduler.add_job(flush_click_counts, "interval", seconds=60, id="flush_clicks")
    scheduler.add_job(cleanup_expired_urls, "interval", hours=1, id="cleanup_expired")
    scheduler.start()

    yield

    scheduler.shutdown()
    await engine.dispose()


app = FastAPI(title="URL Shortener", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(urls.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(redirect.router)

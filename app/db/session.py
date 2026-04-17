from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    # pool_size: persistent connections kept open between requests.
    # max_overflow: extra connections allowed when pool_size is exhausted.
    # Total max connections = pool_size + max_overflow = 15.
    # Tune these via env vars if the deployment target imposes a connection limit
    # (e.g. Supabase free tier allows 15 simultaneous connections).
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

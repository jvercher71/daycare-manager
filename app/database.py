import os
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import settings


def _normalize_db_url(url: str) -> str:
    """Adapt a configured DATABASE_URL to the async drivers this app uses."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif url.startswith("sqlite:///"):
        # Use aiosqlite for SQLite (dev/test)
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)

    # asyncpg rejects libpq-only query params (sslmode, pgbouncer, ...). Strip
    # them so a pasted Supabase URL with "?sslmode=require" still connects;
    # asyncpg negotiates SSL with Supabase automatically.
    parts = urlsplit(url)
    if parts.query:
        drop = {"sslmode", "pgbouncer", "channel_binding",
                "statement_cache_size", "prepared_statement_cache_size"}
        kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                if k.lower() not in drop]
        url = urlunsplit((parts.scheme, parts.netloc, parts.path,
                          urlencode(kept), parts.fragment))
    return url


database_url = _normalize_db_url(settings.DATABASE_URL)

if database_url.startswith("sqlite"):
    engine = create_async_engine(database_url, connect_args={"check_same_thread": False})
else:
    # Postgres (Supabase). On Vercel's serverless functions we connect through
    # Supabase's transaction pooler (PgBouncer): asyncpg's prepared-statement
    # cache is incompatible with transaction pooling, and the external pooler
    # owns connection pooling — so use NullPool and disable statement caching.
    engine = create_async_engine(
        database_url,
        poolclass=NullPool,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

Base = declarative_base()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

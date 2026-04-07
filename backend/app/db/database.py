"""
Database — async SQLAlchemy with RLS context injection.
Every get_db() session automatically sets the Postgres tenant context
so RLS policies fire for ALL queries in that request.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from typing import Optional, AsyncGenerator
from app.core.config import get_settings
import structlog
import os
import re

settings = get_settings()
logger = structlog.get_logger()

_is_testing = os.environ.get("TESTING", "").lower() in ("true", "1", "yes")


def _clean_url(url: str) -> str:
    """Remove sslmode/ssl query params — asyncpg handles SSL via connect_args."""
    url = re.sub(r'[?&]sslmode=[^&]*', '', url)
    url = re.sub(r'[?&]ssl=[^&]*', '', url)
    url = re.sub(r'[?&]$', '', url)
    return url


def _build_connect_args(url: str) -> dict:
    """
    Build asyncpg connect_args.
    asyncpg does NOT accept sslmode — SSL must be passed as ssl.SSLContext object.
    Automatically adds SSL for hosted providers like Neon, Supabase, RDS.
    """
    if "asyncpg" not in url:
        return {}
    args = {
        "server_settings": {
            "application_name": "regulai_test" if _is_testing else "regulai_api",
        }
    }
    if not _is_testing:
        args["server_settings"]["statement_timeout"] = str(
            settings.DATABASE_STATEMENT_TIMEOUT_MS
        )
    hosted_keywords = ["neon.tech", "supabase.co", "amazonaws.com", "render.com"]
    if any(kw in url for kw in hosted_keywords):
        import ssl as _ssl
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        args["ssl"] = ctx
    return args


_clean_db_url = _clean_url(settings.DATABASE_URL)

if _is_testing:
    from sqlalchemy.pool import NullPool
    engine = create_async_engine(
        _clean_db_url,
        echo=False,
        poolclass=NullPool,
        connect_args=_build_connect_args(_clean_db_url),
    )
else:
    engine = create_async_engine(
        _clean_db_url,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        connect_args=_build_connect_args(_clean_db_url),
    )

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db(tenant_id: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Database session dependency.
    Sets RLS tenant context if tenant_id is provided.
    """
    async with AsyncSessionLocal() as session:
        try:
            if tenant_id:
                await session.execute(
                    text("SELECT set_config('app.current_tenant_id', :tid, TRUE)"),
                    {"tid": str(tenant_id)},
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_with_rls(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """Explicit RLS-scoped session for use outside FastAPI dependency injection."""
    async for session in get_db(tenant_id=tenant_id):
        yield session


async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    """Admin session that bypasses RLS (for seed scripts and migrations)."""
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(
                text("SELECT set_config('app.bypass_rls', 'on', TRUE)")
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialise database: create extensions and all tables.
    Called once on application startup and in tests.
    """
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))
        except Exception:
            pass

    # Import ALL models so every table is registered with Base.metadata
    from app.db import models  # noqa
    from app.api.v1.endpoints import allowable_limits  # noqa
    from app.api.v1.endpoints import ingredient_specs   # noqa
    from app.api.v1.endpoints import labeling           # noqa
    from app.api.v1.endpoints import licensing          # noqa
    from app.api.v1.endpoints import alerts             # noqa

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("database_initialized")

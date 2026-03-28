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

settings = get_settings()
logger = structlog.get_logger()

import os
_is_testing = os.environ.get("TESTING", "").lower() in ("true", "1", "yes")

if _is_testing:
    # Use NullPool in tests to avoid event loop conflicts.
    # NullPool creates a fresh connection per query — no persistent pool
    # so there is no loop-binding issue between test setup and test execution.
    from sqlalchemy.pool import NullPool
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
        connect_args={
            "server_settings": {
                "statement_timeout": "30000",
                "application_name": "regulai_test",
            }
        } if "asyncpg" in settings.DATABASE_URL else {},
    )
else:
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        connect_args={
            "server_settings": {
                "statement_timeout": str(settings.DATABASE_STATEMENT_TIMEOUT_MS),
                "application_name": "regulai_api",
            }
        } if "asyncpg" in settings.DATABASE_URL else {},
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
        # Required extensions
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

        # Optional — pg_stat_statements requires shared_preload_libraries
        # Not available in CI/test Postgres containers — safe to skip
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))
        except Exception:
            pass

    # Import all models so SQLAlchemy knows about every table
    from app.db import models  # noqa

    # Create all tables from the ORM metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("database_initialized")

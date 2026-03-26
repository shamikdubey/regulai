"""
Database — async SQLAlchemy with RLS context injection.
Every get_db() session automatically sets the Postgres tenant context
so RLS policies fire for ALL queries in that request.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text, event
from typing import Optional, AsyncGenerator
from app.core.config import get_settings
import structlog

settings = get_settings()
logger = structlog.get_logger()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    # Statement timeout prevents runaway queries from consuming resources
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
    In most endpoints, tenant_id comes from the authenticated user.
    """
    async with AsyncSessionLocal() as session:
        try:
            if tenant_id:
                # Set the Postgres session variable that RLS policies check
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
    """Explicit RLS-scoped session for use outside of FastAPI dependency injection."""
    async for session in get_db(tenant_id=tenant_id):
        yield session


async def get_admin_db() -> AsyncGenerator[AsyncSession, None]:
    """Admin session that bypasses RLS (for seed scripts and migrations)."""
    async with AsyncSessionLocal() as session:
        try:
            # Bypass RLS for admin operations
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
    async with engine.begin() as conn:
        # Core extensions — required
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        # Optional extension — may not be available in all environments
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))
        except Exception:
            pass  # Not available in CI/test environments — that is fine
    from app.db import models  # noqa — ensure all models are registered
    async with engine.begin() as conn:
        await Base.metadata.create_all(conn)  # type: ignore
    logger.info("database_initialized")

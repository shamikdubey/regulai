"""
Rate limiting middleware.
Uses memory storage by default — works without Redis.
If REDIS_URL is set and reachable, uses Redis for distributed rate limiting.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
import os


def _get_storage_uri():
    """Return Redis URI if available, otherwise use memory."""
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_url:
        # Upstash requires rediss:// (SSL) — fix redis:// automatically
        if redis_url.startswith("redis://") and "upstash.io" in redis_url:
            redis_url = redis_url.replace("redis://", "rediss://", 1)
        return redis_url
    return "memory://"


try:
    storage_uri = _get_storage_uri()
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=storage_uri,
    )
except Exception:
    # Fall back to memory if Redis connection fails
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="memory://",
    )


async def check_tenant_query_limit(user, db: AsyncSession) -> None:
    """
    Check if the tenant has exceeded their daily query limit.
    Raises HTTP 429 if limit exceeded.
    """
    from app.db.models import Tenant, QueryLog
    from datetime import datetime, timezone

    # Get tenant
    result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return

    limit = tenant.query_limit_per_day
    if not limit or limit <= 0:
        return  # No limit set

    # Count today's queries for this tenant
    today_count_result = await db.execute(
        text("""
            SELECT COUNT(*) FROM query_logs
            WHERE tenant_id = :tid
            AND created_at::date = CURRENT_DATE
        """),
        {"tid": str(user.tenant_id)},
    )
    today_count = today_count_result.scalar() or 0

    if today_count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily query limit of {limit} reached. Resets at midnight UTC.",
        )

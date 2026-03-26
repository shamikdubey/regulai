"""
Rate Limiting
=============
Two layers of rate limiting:
  1. Global IP-based: prevents abuse from unauthenticated clients
  2. Per-user JWT-based: enforces tenant query_limit_per_day from DB

Uses slowapi (Starlette-compatible rate limiter backed by Redis).

Install: pip install slowapi
"""
import structlog
from typing import Optional
from fastapi import Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from jose import jwt, JWTError

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


def get_user_identifier(request: Request) -> str:
    """
    Rate limit key function.
    Returns user email from JWT if authenticated, else IP address.
    This means authenticated users get their own bucket (not shared by IP).
    """
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            token = auth[7:]
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": False},
            )
            # Use sub (email) as rate limit key so it's per-user, not per-token
            return f"user:{payload.get('sub', 'unknown')}"
        except JWTError:
            try:
                payload = jwt.get_unverified_claims(auth[7:])
                return f"user:{payload.get('sub', 'unknown')}"
            except Exception:
                pass
    # Fall back to IP
    return f"ip:{get_remote_address(request)}"


# Global limiter instance
# Storage: Redis for distributed deployments, memory for single-node dev
limiter = Limiter(
    key_func=get_user_identifier,
    storage_uri=settings.REDIS_URL,
    default_limits=["200/minute", "2000/hour"],
)


# ── Per-tenant daily query limit (enforced in DB) ─────────────────────────────

async def check_tenant_query_limit(
    user,
    db,
) -> None:
    """
    Check if a tenant has exceeded their daily AI query limit.
    Called explicitly in query, gap_assessment, and dossier endpoints.

    The limit is stored in tenants.query_limit_per_day and tracked
    by counting query_logs rows for today.
    """
    from sqlalchemy import text
    from datetime import date

    result = await db.execute(
        text("""
            SELECT COUNT(*) FROM query_logs
            WHERE tenant_id = :tid
            AND created_at::date = CURRENT_DATE
        """),
        {"tid": str(user.tenant_id)},
    )
    today_count = result.scalar() or 0

    # Get tenant limit
    tenant_result = await db.execute(
        text("SELECT query_limit_per_day FROM tenants WHERE id = :tid"),
        {"tid": str(user.tenant_id)},
    )
    row = tenant_result.fetchone()
    limit = row[0] if row else 500

    if today_count >= limit:
        logger.warning(
            "query_limit_exceeded",
            tenant_id=str(user.tenant_id),
            today_count=today_count,
            limit=limit,
        )
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Daily query limit exceeded",
                "limit": limit,
                "used": today_count,
                "reset": "Resets at midnight UTC",
            },
        )

    logger.debug("query_limit_ok", used=today_count, limit=limit)

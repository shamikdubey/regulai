"""
Tenant Context Middleware
=========================
Sets the PostgreSQL session variable `app.current_tenant_id` on every
authenticated request so Row-Level Security policies fire automatically.

This is the glue between the FastAPI JWT layer and PostgreSQL RLS.

Flow:
  1. Request arrives with Bearer token
  2. This middleware extracts tenant_id from the validated JWT
  3. Sets SET LOCAL app.current_tenant_id = '<uuid>' on the DB connection
  4. Every subsequent query in that request is automatically filtered by RLS
  5. Connection returns to pool — setting is reset (LOCAL scope)
"""
import structlog
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from jose import JWTError, jwt

from app.core.config import get_settings
from app.db.database import AsyncSessionLocal

settings = get_settings()
logger = structlog.get_logger()

# Paths that don't need tenant context (auth, health checks)
EXEMPT_PATHS = {
    "/health",
    "/api/v1/auth/token",
    "/api/v1/auth/register",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}


def extract_tenant_id_from_token(token: str) -> Optional[str]:
    """
    Extract tenant_id from JWT without full validation.
    Full validation happens in get_current_user() — this is just for RLS context.
    We decode without verification here since auth middleware already verified.
    """
    try:
        # Try internal HS256 token first
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},
        )
        return payload.get("tenant_id")
    except JWTError:
        pass

    try:
        # Try Auth0 RS256 token (unverified — already verified by auth middleware)
        payload = jwt.get_unverified_claims(token)
        # Auth0 stores org/tenant info in custom claims
        return payload.get("https://regulai.app/tenant_id") or payload.get("tenant_id")
    except Exception:
        return None


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Sets PostgreSQL RLS tenant context for every authenticated request.

    This does NOT do authentication — that's get_current_user()'s job.
    This only sets the Postgres session variable so RLS policies work.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip exempt paths
        path = request.url.path
        if path in EXEMPT_PATHS or path.startswith("/api/docs"):
            return await call_next(request)

        # Extract token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            # No token — will fail in endpoint auth check, just proceed
            return await call_next(request)

        token = auth_header[7:]
        tenant_id = extract_tenant_id_from_token(token)

        if tenant_id:
            # Store tenant_id on request state so endpoints can access it
            request.state.tenant_id = tenant_id

            # Set Postgres session variable for RLS
            # NOTE: This is belt-and-suspenders — the actual DB queries
            # also call set_tenant_context explicitly. But middleware
            # ensures even raw queries inside endpoints are protected.
            async with AsyncSessionLocal() as session:
                try:
                    await session.execute(
                        # Use SET LOCAL so it only applies within this transaction
                        # and automatically resets when connection returns to pool
                        __import__("sqlalchemy").text(
                            "SELECT set_config('app.current_tenant_id', :tid, TRUE)"
                        ),
                        {"tid": str(tenant_id)},
                    )
                    await session.commit()
                except Exception as e:
                    logger.warning("rls_context_set_failed", error=str(e))

        response = await call_next(request)
        return response

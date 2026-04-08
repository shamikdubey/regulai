"""
Rate limiting middleware.
Uses memory storage by default — works without Redis.
If REDIS_URL is set and reachable, uses Redis for distributed rate limiting.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_storage_uri():
    """Return Redis URI if available, otherwise use memory."""
    import os
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

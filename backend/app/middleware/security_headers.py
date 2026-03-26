"""
Security Headers Middleware
===========================
Adds HTTP security headers to every response.
These are required before going to production.

Headers added:
  - Strict-Transport-Security (HSTS) — forces HTTPS
  - X-Content-Type-Options — prevents MIME sniffing
  - X-Frame-Options — prevents clickjacking
  - X-XSS-Protection — legacy XSS filter
  - Referrer-Policy — controls referrer leakage
  - Content-Security-Policy — controls resource loading
  - Permissions-Policy — disables browser features not needed
  - Cache-Control — prevents caching of sensitive API responses
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import get_settings

settings = get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        # HSTS: force HTTPS for 1 year, include subdomains
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent embedding in iframes (clickjacking)
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection (modern browsers use CSP instead)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        # Tight for API responses — no scripts/styles/forms should load from API
        if request.url.path.startswith("/api/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; "
                "frame-ancestors 'none';"
            )
        else:
            # Docs UI needs some relaxation
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
                "img-src 'self' data:; "
                "frame-ancestors 'none';"
            )

        # Disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), "
            "payment=(), usb=(), bluetooth=()"
        )

        # API responses should not be cached by default
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response

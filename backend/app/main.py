
"""
RegulAI FastAPI Application — Phase 0 Production Hardened
"""
import uuid, time, structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import get_settings
from app.core.secrets import load_secrets
from app.services.observability import configure_structlog, metrics
from app.db.database import init_db
from app.middleware.tenant_context import TenantContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limit import limiter

from app.api.v1.endpoints import (
    admin_panel,
    compliance_review,
    document_editor,
    filing_wizard,
    query, regulations, documents, audit, tenants, health, auth,
    gap_assessment, dossier, alerts,
    ingredient_specs, allowable_limits, labeling, licensing,
    privacy, billing
)

load_secrets()
configure_structlog()
settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", version=settings.VERSION, env=settings.ENVIRONMENT,
                cors=settings.CORS_ORIGINS, s3=settings.use_s3)
    await init_db()
    logger.info("database_ready")
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT,
                            release=settings.VERSION, send_default_pii=False,
                            integrations=[FastApiIntegration(transaction_style="url")])
        except ImportError:
            pass
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="RegulAI API", description="Global Regulatory Compliance AI",
        version=settings.VERSION,
        docs_url="/api/docs" if settings.show_docs else None,
        redoc_url="/api/redoc" if settings.show_docs else None,
        openapi_url="/api/openapi.json" if settings.show_docs else None,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    if settings.is_production:
        trusted = []
        for origin in settings.CORS_ORIGINS:
            h = origin.replace("https://","").replace("http://","").split(":")[0]
            trusted.append(h)
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted + ["localhost","127.0.0.1","regulai.onrender.com"])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET","POST","PUT","DELETE","OPTIONS","PATCH"],
        allow_headers=["Authorization","Content-Type","X-Request-ID","Accept"],
        expose_headers=["X-Request-ID","X-RateLimit-Limit","X-RateLimit-Remaining"],
        max_age=86400,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(TenantContextMiddleware)

    @app.middleware("http")
    async def request_tracking(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start = time.monotonic()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id,
            method=request.method, path=request.url.path)
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("request", status=response.status_code,
                    duration_ms=round((time.monotonic()-start)*1000))
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": [{"msg": str(e.get("msg", "")), "loc": e.get("loc", [])} for e in exc.errors()]})

    @app.exception_handler(Exception)
    async def global_error(request: Request, exc: Exception):
        logger.error("unhandled", error=str(exc), type=type(exc).__name__)
        if settings.is_production:
            return JSONResponse(status_code=500,
                content={"detail": "An unexpected error occurred."})
        import traceback
        return JSONResponse(status_code=500,
            content={"detail": str(exc), "traceback": traceback.format_exc()})

    app.include_router(health.router, tags=["Health"])
    app.include_router(auth.router,             prefix="/api/v1", tags=["Auth"])
    app.include_router(query.router,            prefix="/api/v1", tags=["Query"])
    app.include_router(regulations.router,      prefix="/api/v1/regulations",   tags=["Regulations"])
    app.include_router(documents.router,        prefix="/api/v1/documents",     tags=["Documents"])
    app.include_router(audit.router,            prefix="/api/v1/audit",         tags=["Audit"])
    app.include_router(tenants.router,          prefix="/api/v1/tenants",       tags=["Tenants"])
    app.include_router(gap_assessment.router,   prefix="/api/v1",               tags=["Gap Assessment"])
    app.include_router(dossier.router,          prefix="/api/v1",               tags=["Dossier"])
    app.include_router(alerts.router,           prefix="/api/v1",               tags=["Alerts"])
    app.include_router(ingredient_specs.router, prefix="/api/v1",               tags=["Ingredient Specs"])
    app.include_router(allowable_limits.router, prefix="/api/v1",               tags=["Allowable Limits"])
    app.include_router(labeling.router,         prefix="/api/v1",               tags=["Labeling"])
    app.include_router(licensing.router,        prefix="/api/v1",               tags=["Licensing"])
    app.include_router(privacy.router,          prefix="/api/v1",               tags=["Privacy"])
    app.include_router(billing.router,          prefix="/api/v1",               tags=["Billing"])
    app.include_router(filing_wizard.router,    prefix="/api/v1",               tags=["Filing Wizard"])
    app.include_router(document_editor.router,  prefix="/api/v1",               tags=["Document Editor"])
    app.include_router(compliance_review.router, prefix="/api/v1",              tags=["Compliance Review"])
    app.include_router(admin_panel.router,       prefix="/api/v1",               tags=["Admin"])

    return app


app = create_app()

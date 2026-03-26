"""Health & Metrics — Phase 4"""
import time, json
from fastapi import APIRouter, Response, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.config import get_settings
from app.services.observability import metrics, get_circuit_breaker_status

router = APIRouter()
settings = get_settings()
_start = time.time()


@router.get("/health", tags=["Health"])
async def health(db: AsyncSession = Depends(get_db)):
    checks = {}; ok = True

    try:
        t = time.monotonic()
        await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy", "latency_ms": round((time.monotonic()-t)*1000)}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}; ok = False

    try:
        import redis as _r; t = time.monotonic()
        _r.from_url(settings.REDIS_URL, socket_connect_timeout=2).ping()
        checks["redis"] = {"status": "healthy", "latency_ms": round((time.monotonic()-t)*1000)}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}; ok = False

    checks["llm"] = {
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "openai": bool(settings.OPENAI_API_KEY),
        "default": settings.DEFAULT_LLM,
        "status": "healthy" if (settings.ANTHROPIC_API_KEY or settings.OPENAI_API_KEY) else "degraded",
    }
    if not (settings.ANTHROPIC_API_KEY or settings.OPENAI_API_KEY): ok = False

    if settings.ENABLE_CELERY:
        try:
            from app.celery_app import celery_app
            active = celery_app.control.inspect(timeout=2).active()
            checks["celery"] = {"status": "healthy" if active else "degraded", "workers": list(active.keys()) if active else []}
        except Exception as e:
            checks["celery"] = {"status": "degraded", "error": str(e)}
    else:
        checks["celery"] = {"status": "disabled"}

    checks["circuit_breakers"] = get_circuit_breaker_status()
    checks["storage"] = {"type": "s3" if settings.use_s3 else "local", "status": "healthy"}

    metrics.gauge("api.health", 1 if ok else 0)
    body = {"status": "healthy" if ok else "unhealthy", "version": settings.VERSION,
            "environment": settings.ENVIRONMENT, "uptime_seconds": round(time.time()-_start),
            "checks": checks}
    return Response(content=json.dumps(body), media_type="application/json", status_code=200 if ok else 503)


@router.get("/health/live", tags=["Health"])
async def liveness():
    return {"status": "alive", "version": settings.VERSION}


@router.get("/health/ready", tags=["Health"])
async def readiness(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1")); return {"status": "ready"}
    except Exception:
        return Response(content='{"status":"not_ready"}', media_type="application/json", status_code=503)


@router.get("/metrics", tags=["Monitoring"])
async def prometheus():
    return PlainTextResponse(metrics.prometheus_format(), media_type="text/plain; version=0.0.4")


@router.get("/metrics/json", tags=["Monitoring"])
async def json_metrics():
    return metrics.summary()


@router.get("/health/circuit-breakers", tags=["Monitoring"])
async def cb_status():
    return get_circuit_breaker_status()

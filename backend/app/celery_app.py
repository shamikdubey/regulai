"""
Celery Application — Phase 2 Async Job Queue
=============================================
Used for:
  - Gap Assessment (30–90s AI processing across multiple jurisdictions)
  - Dossier Drafting (60–120s multi-section document generation)
  - Document ingestion (chunk + embed uploaded PDFs)

Why Celery:
  - HTTP requests time out at ~30s through load balancers
  - Long AI tasks block Uvicorn workers, degrading responsiveness for other users
  - Celery workers scale independently from API workers

Architecture:
  API worker    → enqueues job → Redis broker
  Celery worker → executes job → stores result in Redis
  API client    → polls GET /jobs/{id} or receives SSE progress updates

Configuration:
  CELERY_BROKER: Redis db 4  (separate from session/cache/rate-limit dbs)
  CELERY_BACKEND: Redis db 5 (result storage)
  Result TTL: 1 hour (results auto-expire)
"""
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

# Parse Redis base URL and append database numbers
_redis_base = settings.REDIS_URL.rsplit("/", 1)[0]  # strip db number

celery_app = Celery(
    "regulai",
    broker=f"{_redis_base}/4",
    backend=f"{_redis_base}/5",
    include=[
        "app.tasks.ai_tasks",
        "app.tasks.document_tasks",
    ],
)

celery_app.conf.update(
    # ── Serialization ─────────────────────────────────────────────────────────
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # ── Timeouts ──────────────────────────────────────────────────────────────
    task_soft_time_limit=180,      # 3 min soft limit — task gets SoftTimeLimitExceeded
    task_time_limit=240,           # 4 min hard kill
    task_acks_late=True,           # ACK only after task completes (safer with retries)

    # ── Results ───────────────────────────────────────────────────────────────
    result_expires=3600,           # Results kept in Redis for 1 hour
    task_ignore_result=False,

    # ── Retry behaviour ───────────────────────────────────────────────────────
    task_max_retries=2,
    task_default_retry_delay=10,

    # ── Worker settings ───────────────────────────────────────────────────────
    worker_prefetch_multiplier=1,  # One task at a time per worker (AI tasks are heavy)
    worker_concurrency=2,          # 2 concurrent AI tasks per worker process

    # ── Monitoring ────────────────────────────────────────────────────────────
    worker_send_task_events=True,
    task_send_sent_event=True,

    # ── Beat schedule (periodic tasks) ───────────────────────────────────────
    beat_schedule={
        "cleanup-expired-tokens": {
            "task": "app.tasks.ai_tasks.cleanup_expired_tokens",
            "schedule": 3600.0,    # Every hour
        },
        "refresh-regulatory-alerts": {
            "task": "app.tasks.ai_tasks.refresh_alerts",
            "schedule": 21600.0,   # Every 6 hours
        },
    },

    timezone="UTC",
)

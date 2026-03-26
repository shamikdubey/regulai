FROM python:3.12-slim AS deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev libffi-dev libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS production
RUN useradd --create-home --shell /bin/bash --uid 1001 app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 libffi8 libpq5 curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY --chown=app:app . .
RUN mkdir -p /app/uploads && chown app:app /app/uploads
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", "--bind", "0.0.0.0:8000", \
     "--timeout", "120", "--graceful-timeout", "30", \
     "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]

# RegulAI v4 — Web Deployment Guide

## What changed from v3 (Electron → Web)

| Layer | Before | After |
|---|---|---|
| Frontend | Electron desktop app | React SPA → Nginx → browser |
| Router | HashRouter | BrowserRouter (requires Nginx try_files) |
| Auth | Internal JWT only | Internal JWT + Auth0 stub ready |
| Storage | Local filesystem | S3 (tenant-scoped paths) |
| DB isolation | App-level only | PostgreSQL RLS (database-level) |
| Secrets | .env files | AWS Secrets Manager in production |
| Rate limiting | None | slowapi per-user + Nginx per-IP |
| Connection pool | Direct asyncpg | PgBouncer (transaction mode) |
| Workers | Single Uvicorn | 4x Gunicorn/Uvicorn workers |
| Security headers | None | HSTS, CSP, X-Frame-Options, etc. |

---

## Prerequisites

```bash
docker --version      # 24+
docker-compose --version  # 2.20+
openssl version       # for TLS cert generation
```

---

## Day-Zero Setup (30 minutes)

### 1. Configure environment

```bash
git clone https://github.com/your-org/regulai.git && cd regulai
cp backend/.env.example .env
```

Edit `.env` — all values required for production:
```env
ENVIRONMENT=production
DOMAIN=app.yourdomain.com

# Database — use strong random passwords
POSTGRES_OWNER_PASSWORD=$(openssl rand -hex 24)
POSTGRES_APP_PASSWORD=$(openssl rand -hex 24)
REDIS_PASSWORD=$(openssl rand -hex 24)

# AI keys
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-proj-...

# CRITICAL: must be 64+ random chars
SECRET_KEY=$(openssl rand -hex 32)

# Auth0 (Phase 1 — leave blank for internal JWT during staging)
AUTH0_DOMAIN=
AUTH0_API_AUDIENCE=

# AWS
AWS_REGION=ap-south-1
AWS_S3_BUCKET=regulai-documents-prod

# Monitoring
SENTRY_DSN=
```

### 2. TLS certificates

```bash
mkdir ssl

# Development / staging — self-signed:
openssl req -x509 -newkey rsa:4096 \
  -keyout ssl/key.pem -out ssl/cert.pem \
  -days 365 -nodes \
  -subj "/CN=${DOMAIN:-localhost}"

# Production — use Let's Encrypt or AWS ACM:
# certbot certonly --standalone -d app.yourdomain.com
# cp /etc/letsencrypt/live/app.yourdomain.com/fullchain.pem ssl/cert.pem
# cp /etc/letsencrypt/live/app.yourdomain.com/privkey.pem ssl/key.pem
```

### 3. Start the stack

```bash
# Run DB migration first (uses owner role to create RLS policies)
docker-compose run --rm migrate

# Start all services
docker-compose up -d

# Watch backend logs
docker-compose logs -f backend

# Verify health
curl -sk https://localhost/health | python3 -m json.tool
```

### 4. Seed data + create admin user

```bash
# Seed regulatory data
docker-compose exec backend python -m scripts.seed_data
docker-compose exec backend python -m scripts.seed_corpus

# Create first admin user
curl -sk -X POST https://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourco.com","password":"StrongPass123!","full_name":"Admin","tenant_name":"Your Company"}'

# Get token
TOKEN=$(curl -sk -X POST https://localhost/api/v1/auth/token \
  -d "username=admin@yourco.com&password=StrongPass123!" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Seed all reference data
curl -sk -X POST https://localhost/api/v1/alerts/seed -H "Authorization: Bearer $TOKEN"
curl -sk -X POST https://localhost/api/v1/ingredient-specs/seed -H "Authorization: Bearer $TOKEN"
curl -sk -X POST https://localhost/api/v1/allowable-limits/seed -H "Authorization: Bearer $TOKEN"
curl -sk -X POST https://localhost/api/v1/labeling-requirements/seed -H "Authorization: Bearer $TOKEN"
curl -sk -X POST https://localhost/api/v1/licensing-pathways/seed -H "Authorization: Bearer $TOKEN"

# Load 110-country batch data
docker-compose exec backend python -m scripts.load_all_batches
```

### 5. Access the app

Open `https://your-domain.com` in a browser.
Sign in with the admin credentials created above.

---

## Architecture

```
Browser → Nginx (TLS + SPA) → FastAPI (4 workers) → PgBouncer → PostgreSQL (RLS)
                                                  ↘ Redis (cache/sessions/rate limits)
                                                  ↘ S3 (tenant-scoped documents)
                                                  ↘ Anthropic/OpenAI (AI queries)
```

## Security model

| Layer | What it protects |
|---|---|
| TLS 1.3 | All data in transit |
| CORS exact origins | Prevents cross-origin API calls |
| HSTS preload | Forces HTTPS on returning visitors |
| PostgreSQL RLS | Database-level tenant isolation |
| S3 path prefix | `documents/{tenant_id}/` — no cross-tenant access |
| JWT auth | Every API endpoint requires valid token |
| slowapi rate limits | Per-user 200/min, login 10/min |
| Nginx rate limits | Per-IP backup layer |
| Secrets Manager | API keys never in environment files |

## Phase 1 next steps (Auth0 + refresh tokens)

1. Create Auth0 tenant at auth0.com
2. Create API (audience = `https://api.yourdomain.com`)
3. Create SPA application (type: Single Page Application)
4. Set `AUTH0_DOMAIN` and `AUTH0_API_AUDIENCE` in .env
5. Update `web/src/pages/LoginPage.tsx` to add Auth0 login button

## Monitoring commands

```bash
# Service health
docker-compose ps

# Backend logs (structured JSON)
docker-compose logs -f backend | python3 -m json.tool

# DB connection pool stats
docker-compose exec pgbouncer psql -h 127.0.0.1 -p 6432 \
  -U pgbouncer_admin pgbouncer -c "SHOW POOLS;"

# Redis memory
docker-compose exec redis redis-cli -a $REDIS_PASSWORD info memory

# Table row counts
docker-compose exec postgres psql -U regulai_owner regulai -c \
  "SELECT tablename, n_live_tup AS rows FROM pg_stat_user_tables ORDER BY rows DESC;"

# Active DB connections
docker-compose exec postgres psql -U regulai_owner regulai -c \
  "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
```

# RegulAI — Global Regulatory Compliance AI Platform

**Version 5.0 · Production-ready web application**

AI-powered regulatory compliance intelligence across **110 countries**, **5 domains**, and **50+ regulatory bodies** — covering food safety, pharmaceuticals, medical devices, nutraceuticals, and traditional medicine.

---

## Architecture

```
Browser ──────────────────────────────────────────────────────────────────
  │  HTTPS                                                               │
  ▼                                                                      │
Nginx (TLS · SPA routing · rate limiting · SSE proxy)                   │
  ├─ /           → React SPA (CloudFront CDN in production)             │
  └─ /api/*      → FastAPI (4× Gunicorn/Uvicorn workers)               │
                     │                                                    │
                     ├─ PostgreSQL 16 + pgvector                         │
                     │   └─ PgBouncer (connection pooling)               │
                     ├─ Redis (sessions · cache · rate limits · Celery)  │
                     ├─ Celery Worker (AI background jobs)               │
                     ├─ AWS S3 (tenant-isolated document storage)        │
                     └─ Anthropic Claude / OpenAI GPT-4o (LLM)          │
                                                                         │
         ◄──── SSE token stream ─────────────────────────────────────────┘
```

## Features

| Module | Description |
|---|---|
| **AI Query** | Real-time streaming compliance Q&A over 110-country regulatory corpus |
| **Gap Assessment** | Multi-jurisdiction compliance gap analysis (async Celery job) |
| **Dossier Drafting** | AI-generated CTD / FSSAI / 510K submission sections |
| **Ingredient Specs** | USP, EP, BP, JECFA, FSSAI pharmacopoeial monographs |
| **Allowable Limits** | Additives, contaminants, pesticide MRLs, nutrient RVs across 110 countries |
| **Labeling Rules** | Mandatory fields, allergens, NIP format, warning seal requirements |
| **Licensing Navigator** | Step-by-step pathways, prerequisites, fees, timelines |
| **Regulatory Alerts** | Monitoring for regulatory changes with email digest |
| **Document Corpus** | Upload PDFs/DOCX → chunk → embed → hybrid RAG search |
| **Audit Log** | HMAC-signed immutable query log for compliance evidence |
| **Billing** | Stripe subscription management (Starter / Growth / Business / Enterprise) |
| **GDPR/DPDP** | Right to erasure, data export, PII detection, consent management |

---

## Quick Start (Development)

### Prerequisites
- Docker 24+ and Docker Compose 2.20+
- OpenSSL (for TLS cert generation)

### 1. Configure environment

```bash
git clone https://github.com/your-org/regulai.git
cd regulai
cp backend/.env.example .env
```

Edit `.env` — minimum required for dev:

```env
ENVIRONMENT=development
POSTGRES_OWNER_PASSWORD=dev_owner_secret
POSTGRES_APP_PASSWORD=dev_app_secret
REDIS_PASSWORD=dev_redis_secret
SECRET_KEY=dev-secret-key-32-chars-minimum
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-proj-...
```

### 2. Generate TLS certificate

```bash
mkdir ssl
openssl req -x509 -newkey rsa:4096 \
  -keyout ssl/key.pem -out ssl/cert.pem \
  -days 365 -nodes -subj "/CN=localhost"
```

### 3. Start the stack

```bash
# Run database migrations first
docker-compose run --rm migrate

# Start all services
docker-compose up -d

# Watch backend logs
docker-compose logs -f backend
```

### 4. Seed data and create admin

```bash
# Create first admin user
curl -k -X POST https://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourco.com","password":"Admin1234!","full_name":"Admin","tenant_name":"Your Company"}'

# Get auth token
TOKEN=$(curl -ks -X POST https://localhost/api/v1/auth/token \
  -d "username=admin@yourco.com&password=Admin1234!" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Seed all reference data
for endpoint in alerts ingredient-specs allowable-limits labeling-requirements licensing-pathways; do
  curl -ks -X POST "https://localhost/api/v1/$endpoint/seed" -H "Authorization: Bearer $TOKEN"
done

# Load 110-country batch data
docker-compose exec backend python -m scripts.seed_data
docker-compose exec backend python -m scripts.load_all_batches
```

### 5. Open the app

```
https://localhost
```

Sign in with `admin@yourco.com` / `Admin1234!`.

---

## Development

### Frontend (web)

```bash
cd web
npm install
npm run dev          # Vite dev server on http://localhost:5173 (proxies /api to localhost:8000)
npm run build        # Production build → web/dist/
npm run typecheck    # TypeScript check
```

### Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Run tests

```bash
cd backend

# Unit + integration tests (requires running Postgres + Redis)
pytest tests/test_api.py -v --tb=short

# Load test (requires running server)
pip install locust
LOCUST_EMAIL=admin@yourco.com LOCUST_PASSWORD=Admin1234! \
  locust -f tests/load_test.py --host https://localhost \
    --users 20 --spawn-rate 2 --run-time 60s --headless
```

### Database migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "describe change"

# Apply all pending migrations
alembic upgrade head

# Downgrade one step
alembic downgrade -1
```

---

## Production Deployment

See [DEPLOY.md](./DEPLOY.md) for the full deployment runbook including:
- AWS ECS Fargate setup
- RDS Aurora Serverless v2
- ElastiCache Redis Cluster
- Auth0 production tenant configuration
- Stripe subscription setup
- SES email verification

### CI/CD

- **Every PR**: `ci.yml` runs backend tests, frontend build, security scanning
- **Push to `main`**: `deploy.yml` builds Docker images, deploys to staging, runs smoke test
- **Production**: Requires manual approval in GitHub Environments, RDS snapshot before migration, blue-green deploy, automatic rollback on failure

---

## Security

| Layer | Implementation |
|---|---|
| Transport | TLS 1.3 only, HSTS preload |
| CORS | Exact origin allowlist — no wildcards |
| Authentication | Auth0 RS256 JWT (production) / internal HS256 (dev) |
| Session management | Refresh token rotation with theft detection; family revocation |
| Database isolation | PostgreSQL Row-Level Security on all tenant-scoped tables |
| Document storage | S3 path prefix `documents/{tenant_id}/` — structural isolation |
| Secrets | AWS Secrets Manager in production |
| Rate limiting | Per-user slowapi + per-IP Nginx |
| Security headers | HSTS, X-Frame-Options DENY, X-Content-Type-Options, CSP |
| LLM resilience | Circuit breaker + automatic GPT-4o fallback |

---

## Regulatory Coverage

**110 countries** across 10 regions, 3 data tiers:

| Tier | Countries | Coverage |
|---|---|---|
| T1 — Full | India, USA, EU, China, Japan, UK, Brazil, Australia, Canada, Singapore | All 5 data types |
| T2 — Core | South Korea, Indonesia, Thailand, Malaysia, Philippines, UAE, Saudi Arabia, Turkey, Israel, South Africa, Nigeria, Kenya, Ghana, New Zealand, Mexico, Argentina, Colombia, Chile, Peru, Switzerland, Norway, Russia, Poland, Kazakhstan + more | Regulatory bodies, licensing, limits, labeling |
| T3 — Basic | 66 remaining countries across Africa, Central America, Eastern Europe, Middle East | Regulatory authority + licensing authority |

**5 domains**: Food & Food Additives · Pharmaceuticals/APIs · Medical Devices · Nutraceuticals/Supplements · Ayurveda/Traditional Medicine

---

## API Reference

Swagger UI (dev/staging only): `https://your-domain/api/docs`

Core endpoints:

```
POST /api/v1/auth/token          Login → access + refresh token
POST /api/v1/auth/refresh        Rotate refresh token
POST /api/v1/query/stream        SSE streaming AI compliance query
POST /api/v1/query               Synchronous AI query (fallback)
POST /api/v1/gap-assessment      Enqueue multi-jurisdiction gap analysis
POST /api/v1/dossier             Enqueue dossier generation
GET  /api/v1/allowable-limits    Additive/contaminant/pesticide limits
GET  /api/v1/labeling-requirements  Mandatory label requirements
GET  /api/v1/licensing-pathways  Licensing steps, fees, timelines
GET  /api/v1/ingredient-specs    Pharmacopoeial monographs
GET  /api/v1/jobs/{id}          Poll background job status
GET  /api/v1/billing/plans      Pricing (public)
DELETE /api/v1/privacy/me       GDPR right to erasure
GET  /api/v1/privacy/export     Data portability export
GET  /health                    Component health check
GET  /metrics                   Prometheus metrics
```

---

## Monitoring

Import `monitoring/dashboard.json` into Datadog or Grafana for:
- API health, latency p95/p99, error rate
- LLM circuit breaker states
- Celery queue depth and worker health
- PgBouncer connection pool utilisation
- Per-tenant query limit usage
- LLM API spend tracking with alerts

---

## Compliance

| Regulation | Status |
|---|---|
| GDPR (EU) | Right to erasure, portability export, consent management, DPA annexes |
| DPDP Act 2023 (India) | Grievance officer endpoint, consent §6, erasure §13 |
| ISO 27001 | Access controls, audit logging, encryption at rest and in transit |
| SOC 2 Type II | Audit log immutability (HMAC signatures), access review |

---

## License

Copyright © 2026 RegulAI. All rights reserved.

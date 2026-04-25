# Sentinel Guard — Developer Reference

## What This Is

Professional security scanning API. Scans run **only on assets whose ownership has been cryptographically or DNS-verified**. No asset can be scanned without passing through the verification gate.

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Task queue | Celery 5 + Redis 7 |
| Active scan | Nmap (via nmap3) |
| Passive recon | Shodan API |
| TLS analysis | Python ssl + cryptography |
| Header scan | httpx |
| Auth | JWT (HS256) + bcrypt + API keys |
| Report signing | RSA-2048 / PSS / SHA-256 |

## Project Layout

```
sentinel-guard/
├── app/
│   ├── main.py                        # FastAPI entry point, lifespan, middleware
│   ├── core/
│   │   ├── config.py                  # Settings via pydantic-settings (.env)
│   │   ├── database.py                # Async engine + session factory
│   │   └── security.py                # JWT, bcrypt helpers
│   ├── models/                        # SQLAlchemy ORM models
│   │   ├── user.py                    # User + APIKey
│   │   ├── organization.py            # Organization (multi-tenant)
│   │   ├── asset.py                   # Asset + enums (type, verification)
│   │   ├── scan.py                    # Scan + ScanFinding + enums
│   │   └── report.py                  # Report (signed payload)
│   ├── schemas/                       # Pydantic request/response schemas
│   ├── api/
│   │   ├── deps.py                    # Auth dependencies (get_current_user)
│   │   └── v1/
│   │       ├── auth.py                # /register /login /refresh /api-keys
│   │       ├── assets.py              # Asset CRUD + verification flow
│   │       ├── scans.py               # Scan requests + status
│   │       └── reports.py             # Report generation + integrity check
│   ├── services/
│   │   ├── verification/
│   │   │   ├── dns_verifier.py        # DNS TXT record check
│   │   │   ├── http_verifier.py       # HTTP file challenge
│   │   │   ├── whois_verifier.py      # WHOIS email lookup
│   │   │   └── manager.py            # Orchestrates all verifiers
│   │   ├── scanner/
│   │   │   ├── shodan_scanner.py      # Passive recon (Shodan API)
│   │   │   ├── nmap_scanner.py        # Active port/service scan
│   │   │   ├── ssl_scanner.py         # TLS cert + cipher analysis
│   │   │   ├── headers_scanner.py     # HTTP security headers
│   │   │   └── orchestrator.py       # Runs all scanners, aggregates findings
│   │   └── reporter/
│   │       └── generator.py           # RSA-signed JSON report builder
│   └── workers/
│       ├── celery_app.py              # Celery instance + config
│       └── scan_tasks.py              # run_scan task (async inside Celery)
├── alembic/                           # DB migrations
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Running Locally

```bash
# 1. Copy and edit environment
cp .env.example .env

# 2. Start all services
docker compose up --build

# 3. API docs
open http://localhost:8000/docs
```

## Development Workflows

```bash
# Install dependencies
pip install -r requirements.txt

# Run API only (needs external DB + Redis)
uvicorn app.main:app --reload

# Run Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Create a migration after model changes
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head
```

## API Flow

```
1. POST /api/v1/auth/register        → create user + org
2. POST /api/v1/auth/login           → get JWT tokens
3. POST /api/v1/assets               → register asset (domain/IP)
4. GET  /api/v1/assets/{id}/challenge → get verification instructions
5. POST /api/v1/assets/{id}/verify   → confirm ownership
6. POST /api/v1/scans                → queue scan (202 Accepted)
7. GET  /api/v1/scans/{id}           → poll scan status + findings
8. POST /api/v1/reports/generate/{scan_id} → generate signed report
9. GET  /api/v1/reports/{id}/verify  → verify report integrity
```

## Security Architecture

- **No unverified scans** — `_get_verified_asset()` in `scans.py` enforces `VerificationStatus.VERIFIED` before any scan is queued.
- **Ownership is org-scoped** — all queries filter by `organization_id`; users cannot access other orgs' data.
- **Report integrity** — RSA-2048/PSS signatures allow offline verification of report authenticity.
- **Rate limiting** — `slowapi` middleware applied at app level.
- **Secret key rotation** — RSA key pair is generated once on first run, stored in `keys/`.

## Severity Scoring

Risk score = sum of per-finding weights, capped at 100:

| Severity | Weight |
|----------|--------|
| Critical | 40 |
| High | 20 |
| Medium | 8 |
| Low | 3 |
| Info | 0 |

## Key Conventions

- All IDs are UUID v4.
- Timestamps are UTC ISO-8601 strings in API responses.
- Scanner findings return `severity` as lowercase string matching `Severity` enum.
- Celery tasks run `asyncio.run()` internally — do not nest event loops.
- Add new scanners by implementing `scan(target) -> dict` + `extract_findings(data) -> list[dict]`, then wire into `orchestrator.py`.

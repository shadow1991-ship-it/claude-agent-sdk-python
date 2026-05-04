# Sentinel Guard — Claude Reference

## What This Repository Is

A professional security scanning platform built with FastAPI, PostgreSQL, Celery, and local AI via Docker Model Runner. The core invariant: **no asset can be scanned without cryptographic proof of ownership**. Every scan request validates `VerificationStatus.VERIFIED` before dispatching.

The repo has three runnable components:

| Component | Path | Tech |
|-----------|------|------|
| Backend API + workers | `sentinel-guard/` | FastAPI + Celery + PostgreSQL + Redis |
| Web Dashboard + AI chatbot | `web_dashboard.py` | Flask + SSE streaming |
| CLI / API client | `empire/` | httpx + bash |

---

## Repository Layout

```
sentinel-guard/                    ← main backend (Docker Compose)
  app/
    main.py                        ← FastAPI app, lifespan, CORS, rate limiting
    core/
      config.py                    ← pydantic-settings, reads .env
      database.py                  ← async SQLAlchemy engine + session factory
      security.py                  ← bcrypt, JWT helpers (create/decode tokens)
    models/                        ← SQLAlchemy ORM (UUID PKs, JSONB columns)
      user.py                      ← User, APIKey
      organization.py              ← Organization (multi-tenant isolation)
      asset.py                     ← Asset + AssetType/VerificationStatus enums
      scan.py                      ← Scan, ScanFinding, ScanType/ScanStatus/Severity enums
      report.py                    ← Report (RSA-signed payload)
    schemas/                       ← Pydantic v2 request/response schemas
    api/
      deps.py                      ← get_current_user dependency (JWT + APIKey)
      v1/
        auth.py                    ← /register /login /refresh /api-keys
        assets.py                  ← Asset CRUD + /challenge + /verify
        scans.py                   ← Scan CRUD, /sarif export, /findings/{id}/fix
        reports.py                 ← /generate/{scan_id}, /verify
    services/
      verification/
        dns_verifier.py            ← DNS TXT record check
        http_verifier.py           ← HTTP file challenge
        whois_verifier.py          ← WHOIS email lookup
        manager.py                 ← dispatches to the right verifier
      scanner/
        orchestrator.py            ← runs all scanners via asyncio.gather, calculates risk score
        shodan_scanner.py          ← passive recon (Shodan API)
        nmap_scanner.py            ← active port/service scan (nmap3)
        ssl_scanner.py             ← TLS cert + cipher suite analysis
        headers_scanner.py         ← HTTP security headers
        dockerfile_scanner.py      ← rule-based regex + DeepSeek V4 Pro AI
        sbom_scanner.py            ← Syft CLI + AI CVE analysis
        ai_scanner.py              ← post-processing: missed findings + remediation plan
        auto_fixer.py              ← Granite Nano code fixes for findings
      reporter/
        generator.py               ← RSA-2048/PSS signed JSON reports
    workers/
      celery_app.py                ← Celery instance configuration
      scan_tasks.py                ← run_scan task (asyncio.run inside Celery)
  alembic/                         ← DB migrations
  Dockerfile
  docker-compose.yml               ← api + worker + db + redis
  requirements.txt
  .env.example

web_dashboard.py                   ← Flask app: login, dashboard, /api/chat (SSE), /api/scan-dockerfile
empire/
  sentinel_client.py               ← SentinelClient (httpx wrapper) + get_client()
  track.sh                         ← live terminal tracker dashboard
  .env.example

.github/workflows/
  sentinel-scan.yml                ← CI: Dockerfile scanner on every push/PR
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.115 + Uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Task queue | Celery 5 + Redis 7 |
| Active scan | Nmap (nmap3) |
| Passive recon | Shodan API |
| TLS analysis | Python ssl + cryptography |
| Header scan | httpx |
| Dockerfile scan | Rule-based regex + DeepSeek V4 Pro (AI) |
| SBOM | Syft CLI + AI CVE analysis |
| AutoFixer | Granite 4.0 Nano |
| AI routing | Docker Model Runner (local, no API key) |
| Auth | JWT HS256 + bcrypt + API keys |
| Report signing | RSA-2048 / PSS / SHA-256 |
| Rate limiting | slowapi |
| Web Dashboard | Flask + SSE |

---

## Development Workflows

### Start the backend

```bash
cd sentinel-guard
cp .env.example .env          # then set SECRET_KEY

docker compose up --build -d
docker compose exec api alembic upgrade head

# verify
curl http://localhost:8000/health
# Swagger UI: http://localhost:8000/docs
```

### Run components individually (needs external DB + Redis)

```bash
# API
cd sentinel-guard
pip install -r requirements.txt
uvicorn app.main:app --reload

# Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Web dashboard (root of repo)
pip install flask openai
python web_dashboard.py        # http://localhost:5000
```

### Database migrations

```bash
# After changing any model in app/models/
docker compose exec api alembic revision --autogenerate -m "describe change"
docker compose exec api alembic upgrade head
```

### Logs and restart

```bash
docker compose logs api -f
docker compose logs worker -f
docker compose down && docker compose up -d
```

---

## API Flow

```
1.  POST /api/v1/auth/register              → create user + organization
2.  POST /api/v1/auth/login                 → get JWT access + refresh tokens
3.  POST /api/v1/assets                     → register asset (domain/IP/ip_range/url/repository)
4.  GET  /api/v1/assets/{id}/challenge      → verification instructions (DNS TXT / HTTP file / WHOIS)
5.  POST /api/v1/assets/{id}/verify         → confirm ownership → status becomes VERIFIED
6.  POST /api/v1/scans                      → queue scan (202 Accepted)
      body: {asset_id, scan_type, nmap_arguments?, dockerfile_url?, image_ref?}
      scan_type: full | ports | ssl | headers | shodan | dockerfile | sbom
7.  GET  /api/v1/scans/{id}                 → poll status + findings
8.  GET  /api/v1/scans/{id}/sarif           → SARIF 2.1.0 export (GitHub Code Scanning compatible)
9.  POST /api/v1/scans/{id}/findings/{f}/fix → AI AutoFixer (Granite Nano)
10. POST /api/v1/reports/generate/{scan_id} → generate RSA-signed report
11. GET  /api/v1/reports/{id}/verify        → verify report integrity offline
```

---

## Security Architecture

- **No unverified scans** — `_get_verified_asset()` in `scans.py:114` enforces `VerificationStatus.VERIFIED` and returns HTTP 403 otherwise. Never bypass this check.
- **Org-scoped isolation** — every query filters by `organization_id`. Users cannot read or modify other organizations' data.
- **Report integrity** — RSA-2048/PSS signatures allow offline verification without calling the API.
- **Rate limiting** — `slowapi` middleware per-endpoint: login 5/min, register 3/min, scan 10/min, default 60/min.
- **Celery + asyncio** — `scan_tasks.py` calls `asyncio.run()` inside each Celery task. Do **not** nest event loops (no `asyncio.run()` inside an already-running loop).

---

## Severity Scoring

Risk score = sum of per-finding weights, capped at 100:

| Severity | Weight |
|----------|--------|
| critical | 40 |
| high | 20 |
| medium | 8 |
| low | 3 |
| info | 0 |

Implemented in `orchestrator.py:_calculate_risk`.

---

## AI Models (Docker Model Runner — local, free, no API key)

| Task | Model env var | Default model | Latency |
|------|--------------|---------------|---------|
| AutoFixer, code gen | `AI_MODEL_FAST` | `ai/granite-4.0-nano` | < 2s |
| Dockerfile deep analysis, CVE reasoning | `AI_MODEL_DEEP` | `ai/deepseek-v4-pro` | < 30s |
| Dashboard chatbot, SSE Q&A | `AI_MODEL_GENERAL` | `ai/deepseek-v4-flash` | < 15s |

Pull models before first use:
```bash
docker model pull ai/deepseek-v4-flash
docker model pull ai/deepseek-v4-pro
docker model pull ai/granite-4.0-nano
```

Set `AI_ENABLED=false` to skip AI layers (used in CI).

---

## Key Conventions

- All primary keys are UUID v4.
- Timestamps are stored as `DateTime(timezone=True)` and serialized as UTC ISO-8601 strings in API responses.
- Scanner findings use `severity` as a lowercase string matching the `Severity` enum (`critical | high | medium | low | info`).
- All scanner raw data is stored per-column as JSONB on the `Scan` row (`shodan_data`, `nmap_data`, etc.).
- CORS and `ALLOWED_HOSTS` accept comma-separated strings in `.env`; `*` disables restrictions.

### Adding a new scanner

1. Create `sentinel-guard/app/services/scanner/my_scanner.py` with two async methods:
   - `scan(target: str) -> dict` — runs the scan, returns raw data
   - `extract_findings(data: dict) -> list[dict]` — normalizes to finding dicts
2. Import and instantiate in `orchestrator.py`; add to `tasks` dict in `ScanOrchestrator.run()`.
3. Add a `my_data` JSONB column to the `Scan` model, create an Alembic migration.

---

## CI/CD

`.github/workflows/sentinel-scan.yml` triggers on any `Dockerfile` change:
- Runs rule-based scanner only (`AI_ENABLED=false` — no Docker Model Runner in CI).
- Fails the build on any **critical** finding.
- Outputs JSON findings to stdout.

---

## Environment Variables Reference

All vars read from `sentinel-guard/.env` via pydantic-settings. Defaults are in `app/core/config.py`.

| Variable | Default | Notes |
|----------|---------|-------|
| `SECRET_KEY` | `change-me...` | **Must change.** Use `secrets.token_urlsafe(64)` |
| `DATABASE_URL` | `postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_db` | Use docker-compose defaults |
| `REDIS_URL` | `redis://localhost:6379/0` | |
| `SHODAN_API_KEY` | `""` | Optional, from shodan.io |
| `DEBUG` | `false` | Set `true` only in dev |
| `CORS_ORIGINS` | `*` | Comma-separated in production |
| `ALLOWED_HOSTS` | `*` | Comma-separated in production |
| `AI_ENABLED` | `true` | Set `false` to skip all AI calls |
| `DOCKER_MODEL_RUNNER_URL` | `http://localhost:12434/engines/llama.cpp/v1` | |
| `AI_MODEL_FAST` | `ai/granite-4.0-nano` | AutoFixer |
| `AI_MODEL_DEEP` | `ai/deepseek-v4-pro` | Dockerfile + SBOM |
| `AI_MODEL_GENERAL` | `ai/deepseek-v4-flash` | Chatbot |

Web dashboard reads from `empire/.env`:

| Variable | Default |
|----------|---------|
| `SENTINEL_API_URL` | `http://localhost:8000/api/v1` |
| `DASHBOARD_SECRET` | `change-me-in-production-64-chars` |
| `DASHBOARD_PASSWORD` | `alhakim2026` ← change this |
| `DASHBOARD_PORT` | `5000` |

---

## Common Lint / Type Commands

```bash
# Lint and auto-fix (run from repo root, targets sentinel-guard source)
python -m ruff check sentinel-guard/app/ --fix
python -m ruff format sentinel-guard/app/

# Typecheck
python -m mypy sentinel-guard/app/

# Tests (if added)
python -m pytest tests/
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| API exits immediately | `SECRET_KEY` empty or `.env` missing | Copy `.env.example`, set key |
| `scan` stays `queued` | Redis not reachable | `docker compose restart redis worker` |
| AI returns empty findings | Model Runner not running | Check Docker Desktop → Enable Model Runner |
| `alembic: not found` | Running outside container | `docker compose exec api alembic ...` |
| Port 5432 already in use | Local Postgres conflict | Change port in `docker-compose.yml` |

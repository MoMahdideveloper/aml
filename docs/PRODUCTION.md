# Platinum Heritage CRM — Production runbook

## Prerequisites

- Python 3.11+
- Node.js 18+ (for CSS build)
- Postgres recommended (`DATABASE_URL`); SQLite OK for small demos only
- Strong `SESSION_SECRET`

## 1. Environment

```bash
export FLASK_ENV=production
export SESSION_SECRET="$(openssl rand -hex 32)"   # or equivalent
export DATABASE_URL="postgresql://user:pass@host:5432/gptvli"
export ENABLE_CSRF=1                              # default on when FLASK_ENV=production
export USE_TAILWIND_CDN=0                         # use built CSS (default in production)
export SESSION_COOKIE_SECURE=1                    # HTTPS only cookies
# Optional integrations
export GOOGLE_API_KEY=...
export SMS_PROVIDER=log                           # or melipayamak
export GEOCODE_PROVIDER=auto                      # nominatim / off
```

Copy secrets via your host’s secret store — do **not** commit `.env` with real keys.

## 2. Install & migrate

```bash
# Python deps (uv preferred)
uv sync
# or: pip install -r requirements.txt

# DB schema
export FLASK_APP=app.py
flask db upgrade

# Frontend CSS (required for production styling without CDN)
npm install
npm run rebuild:css 2>/dev/null || npm run build:css
```

## 3. Run (WSGI)

```bash
# Example gunicorn (Linux)
gunicorn -w 2 -b 0.0.0.0:8000 "app:create_app()"

# Or module form if app is factory-bound
gunicorn -w 2 -b 0.0.0.0:8000 main:app
```

Windows local smoke:

```powershell
$env:FLASK_ENV="development"
$env:USE_TAILWIND_CDN="1"   # optional CDN for rapid UI work
python main.py
```

### Docker Compose (recommended)

Multi-stage `Dockerfile` builds Tailwind then runs gunicorn as non-root.

**Required env vars (no weak defaults):**
- `SESSION_SECRET` — long random secret (app refuses the default in production)
- `POSTGRES_PASSWORD` — explicit DB password (compose fails without it)

```bash
# Required
export SESSION_SECRET="$(openssl rand -hex 32)"
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
# Optional: WEB_PORT, GOOGLE_API_KEY, RUN_MIGRATIONS=1

# Build & start Postgres + web
docker compose --profile prod up -d --build

# Probes: liveness vs DB readiness
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz

# Logs / stop
docker compose --profile prod logs -f web
docker compose --profile prod down
```

Container entrypoint runs `flask db upgrade heads` when `RUN_MIGRATIONS=1` (default).
Migration failures **exit non-zero** after bounded retries (`MIGRATION_RETRIES`,
`MIGRATION_RETRY_DELAY`) so Gunicorn does not start on a broken schema.
Set `RUN_MIGRATIONS=0` only when migrations are applied externally.

Or via Makefile (Git Bash / WSL / Linux):

```bash
export SESSION_SECRET=...
export POSTGRES_PASSWORD=...
make up-prod
make health
make logs-prod
make down-prod
```

Windows PowerShell:

```powershell
$env:SESSION_SECRET = "your-long-secret"
$env:POSTGRES_PASSWORD = "your-strong-db-password"
.\scripts\up-prod.ps1
```

`up-prod.ps1` waits for **`/readyz`** (not only `/healthz`).

Volumes: `postgres_data` (DB), `uploads_data` (property media). Redis is included in the `prod` profile for optional cache/Celery.

## 4. Health checks

| Path | Purpose |
|------|---------|
| `GET /healthz` | Process up (liveness only) |
| `GET /readyz` | Dependencies ready (DB required; Redis if `READYZ_REQUIRE_REDIS=1`) |
| `GET /metrics` | Prometheus text (HTTP RED, jobs, providers) |

Observability contract: `docs/OBSERVABILITY_CONTRACT.md`. Alerts (proposal only): `docs/ALERTS.md`. Runbooks: `docs/runbooks/`.

CI/CD delivery: `docs/DELIVERY_CONTRACT.md`, `docs/RELEASE_RUNBOOK.md`, `docs/BRANCH_PROTECTION.md` (settings not applied automatically). Staging/production GitHub Actions are **manual + dry_run by default**.

Wire these into load balancers / Kubernetes probes.

## 5. Image packaging boundary

Production `Dockerfile` builds from a filtered context (see `.dockerignore`):

| Included (runtime) | Excluded |
|--------------------|----------|
| `app.py`, `views/`, `templates/` (live only), `static/`, `migrations/`, `services/`, `repositories/` | `templates/_archive/`, `stitch_kpi_performance_dashboard/`, `graphify-out/` |
| `docker/entrypoint.sh`, `requirements.txt` | `tests/`, Track B (`api/`, `matcher/`, `ingestor/`, `chatbot/`) |
| Built CSS in image build stage | `platinum-heritage-runnable/`, agent tooling, local DB/vector data |

Template reference audit (no Stitch dependency):

```bash
python scripts/audit_template_references.py
pytest -q tests/test_template_references.py tests/test_docker_context.py
```

## 6. CSS workflow

| Mode | How |
|------|-----|
| Production | `npm run build:css` → `static/css/tailwind-ph.css`; `USE_TAILWIND_CDN=0` |
| Local UI hack | `USE_TAILWIND_CDN=1` loads Tailwind CDN (not for prod) |
| Watch | `npm run watch:css` while editing templates |

After template class changes, re-run `npm run build:css` before shipping.

## 7. Security checklist

- [ ] `SESSION_SECRET` is unique and long (production refuses default secret)
- [ ] HTTPS terminated (cookie `Secure` + HSTS headers when `FLASK_ENV=production`)
- [ ] `ENABLE_CSRF=1` for form posts
- [ ] Admin routes require auth (`/admin/*`)
- [ ] No API keys in git; rotate leaked keys
- [ ] Review CSP if you add new third-party scripts
- [ ] Backups for `DATABASE_URL` / upload volume (`static/uploads`)
- [ ] Recovery drills documented and tested — see [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md) and [BACKUP_RECOVERY_CONTRACT.md](BACKUP_RECOVERY_CONTRACT.md)

## 8. Post-deploy smoke

```bash
curl -fsS https://your-host/healthz
curl -fsS https://your-host/readyz
curl -fsSI https://your-host/ | head
# Browser: login → dashboard → properties → map → recommendations
```

## 9. Rollback

1. Redeploy previous app image / git tag  
2. `flask db downgrade -1` only if the failed release added a migration you must reverse — prefer **explicit revision** targets when heads were merged  
3. Restore DB snapshot if data migrations were destructive — **disposable restore first**, then switch `DATABASE_URL` only after approval (see [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md))  

### Backup commands (quick reference)

```bash
# SQLite (explicit paths; online backup API)
python scripts/backup_sqlite.py --source ./real_estate_crm.db --dest-dir ./backups

# Postgres (credentials from env only — never on CLI)
# export DATABASE_URL=postgresql://...
python scripts/backup_postgres.py --dest-dir ./backups
```

## 10. CI (GitHub Actions)

Workflow: `.github/workflows/tests.yml`

| Job | What it does | Blocks merge? |
|-----|----------------|---------------|
| **css** | `npm ci` + `npm run build:css`, asserts `tailwind-ph.css` exists | Yes |
| **lint** | Ruff + strict Black on maintained Track A paths | Yes |
| **core-tests** | PH UI + smoke + production config/health/entrypoint tests | Yes |
| **postgres-migrations** | Empty Postgres `flask db upgrade heads` + `/readyz` | Yes |
| **full-tests** | Entire pytest suite (informational; may be flaky) | No |

Local mirror:

```bash
make ci-local
# or:
npm run build:css
pytest -q \
  tests/test_platinum_heritage_ui.py \
  tests/test_app_smoke.py \
  tests/test_simple.py \
  tests/test_template_replacement.py \
  tests/test_production_config.py \
  tests/test_health_readiness.py \
  tests/test_auth_cookie_hardening.py \
  tests/test_docker_entrypoint.py \
  tests/test_dashboard_trends.py
```

## Feature surface (reference)

| Area | Route examples |
|------|----------------|
| CRM | `/`, `/properties`, `/agents`, `/customers`, `/deals`, `/tasks` |
| Insights | `/market`, `/compare`, `/calculators` |
| Outreach | `/messaging`, `/sms` |
| Docs / kiosk | `/contracts`, `/kiosk` |
| Map | `/properties/map` |

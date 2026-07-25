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

The `prod` profile brings up five services: `db`, `redis`, `web` (gunicorn),
`worker` (Celery worker) and `beat` (Celery scheduler). All three app services
read `.env` via compose `env_file:`, then override the infra wiring
(`db`/`redis` hostnames, `RUN_MIGRATIONS`) from the explicit `environment:` block.

**Required env vars (no weak defaults):**
- `SESSION_SECRET` — long random secret (app refuses the default in production)
- `POSTGRES_PASSWORD` — explicit DB password (compose fails without it)
- `ADMIN_PASSWORD` — min 12 chars, not a known-weak value; the app **refuses to
  boot** otherwise. Because it is supplied through `.env`, a missing `env_file:`
  shows up as a health-check failure, not an obvious config error.

```bash
# Required
export SESSION_SECRET="$(openssl rand -hex 32)"
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
# ADMIN_PASSWORD lives in .env (gitignored), e.g.
#   python -c "import secrets; print(secrets.token_urlsafe(20))"
# Optional: WEB_PORT, GOOGLE_API_KEYS, RUN_MIGRATIONS=1

# Build & start the full stack (db + redis + web + worker + beat)
docker compose --profile prod up -d --build

# Probes: liveness vs DB readiness
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz

# All five containers should report (healthy)
docker compose --profile prod ps

# Logs / stop
docker compose --profile prod logs -f web worker beat
docker compose --profile prod down
```

Container entrypoint runs `flask db upgrade heads` when `RUN_MIGRATIONS=1` (default).
Migration failures **exit non-zero** after bounded retries (`MIGRATION_RETRIES`,
`MIGRATION_RETRY_DELAY`) so Gunicorn does not start on a broken schema.
Set `RUN_MIGRATIONS=0` only when migrations are applied externally.

**`web` is the sole migration owner.** Compose pins `RUN_MIGRATIONS=0` on `worker`
and `beat` so three services cannot race the same `alembic upgrade`. Expect
exactly one "Running database migrations" line in `web`, and
"RUN_MIGRATIONS=0 — skipping" in the other two.

**`beat` is the sole scheduler.** Never run a second beat or enable in-process
schedulers alongside it, or every periodic task fires twice.

The image sets `PYTHONPATH=/app`. This is required, not cosmetic: the `celery`,
`gunicorn` and `flask` console scripts put their own `bin` directory on
`sys.path[0]`, so `WORKDIR /app` alone leaves root modules such as
`background_matcher` unimportable and tasks fail with `No module named ...`.
Note that `docker exec … python -c "import background_matcher"` will *succeed*
even when this is broken, because bare `python` adds the cwd — verify through the
real entrypoint instead.

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

Volumes: `postgres_data` (DB), `uploads_data` (property media), `beat_data`
(Celery beat schedule state — keep it so beat does not replay or drop schedules
across restarts).

Redis is **required**, not optional: it is the Celery broker and result backend
for `worker` and `beat`. Both services `depends_on` it with
`condition: service_healthy`.

`.dockerignore` is an **allowlist** (`*` first, then `!` re-includes). Add new
runtime files/dirs there or they will silently be missing from the image. It must
stay LF-only — CRLF makes Docker read `.git\r`, which matches nothing and
previously inflated the build context from ~27MB to 1.1GB. `.gitattributes` pins
this.

## 4. Optional: AI form assist

Default **off**. When enabled, authenticated users get multimodal suggestions on CRM forms; AI never auto-saves records.

```bash
export ENABLE_AI_FORM_ASSIST=0   # keep off until staging review
# export ENABLE_AI_FORM_ASSIST=1
# export GOOGLE_API_KEY=...
# export AI_FORM_AUDIT_STORAGE_ROOT=/var/lib/gptvli/ai_form_audit  # not under static/
# export AI_FORM_RETENTION_DAYS=90
# export AI_FORM_RETENTION_SCHEDULE_ENABLED=0  # set 1 only with Celery Beat
```

Operator contract: `docs/AI_FORM_ASSIST_OPERATOR.md`. Manual purge:

```python
from services.ai_form_assist.retention import cleanup_expired_ai_form_audit
cleanup_expired_ai_form_audit(dry_run=True)   # inventory
cleanup_expired_ai_form_audit(dry_run=False)  # authorized delete
```

## 5. Health checks

| Path | Purpose |
|------|---------|
| `GET /healthz` | Process up (liveness only) |
| `GET /readyz` | Dependencies ready (DB required; Redis if `READYZ_REQUIRE_REDIS=1`) |
| `GET /metrics` | Prometheus text (HTTP RED, jobs, providers) |

Observability contract: `docs/OBSERVABILITY_CONTRACT.md`. Alerts (proposal only): `docs/ALERTS.md`. Runbooks: `docs/runbooks/`.

CI/CD delivery: `docs/DELIVERY_CONTRACT.md`, `docs/RELEASE_RUNBOOK.md`, `docs/BRANCH_PROTECTION.md` (settings not applied automatically). Staging/production GitHub Actions are **manual + dry_run by default**.

Staging rehearsal (local, disposable): `docs/STAGING_RELEASE_REHEARSAL.md` — run `scripts/staging_release_rehearsal.py --dry-run --opt-in` to validate gate wiring without external binaries.

Wire these into load balancers / Kubernetes probes.

## 6. Image packaging boundary

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

## 7. CSS workflow

| Mode | How |
|------|-----|
| Production | `npm run build:css` → `static/css/tailwind-ph.css`; `USE_TAILWIND_CDN=0` |
| Local UI hack | `USE_TAILWIND_CDN=1` loads Tailwind CDN (not for prod) |
| Watch | `npm run watch:css` while editing templates |

After template class changes, re-run `npm run build:css` before shipping.

## 8. Security checklist

- [ ] `SESSION_SECRET` is unique and long (production refuses default secret)
- [ ] HTTPS terminated (cookie `Secure` + HSTS headers when `FLASK_ENV=production`)
- [ ] `ENABLE_CSRF=1` for form posts
- [ ] Admin routes require auth (`/admin/*`)
- [ ] No API keys in git; rotate leaked keys
- [ ] Review CSP if you add new third-party scripts
- [ ] Backups for `DATABASE_URL` / upload volume (`static/uploads`)
- [ ] Recovery drills documented and tested — see [BACKUP_AND_RECOVERY.md](BACKUP_AND_RECOVERY.md) and [BACKUP_RECOVERY_CONTRACT.md](BACKUP_RECOVERY_CONTRACT.md)

## 9. Post-deploy smoke

```bash
curl -fsS https://your-host/healthz
curl -fsS https://your-host/readyz
curl -fsSI https://your-host/ | head
# Browser: login → dashboard → properties → map → recommendations
```

## 10. Rollback

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

## 11. CI (GitHub Actions)

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

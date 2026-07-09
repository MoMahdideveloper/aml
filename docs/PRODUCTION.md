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

```bash
# Required
export SESSION_SECRET="$(openssl rand -hex 32)"
# Optional: POSTGRES_PASSWORD, WEB_PORT, GOOGLE_API_KEY

# Build & start Postgres + web
docker compose --profile prod up -d --build

# Health
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS http://127.0.0.1:8000/readyz

# Logs / stop
docker compose --profile prod logs -f web
docker compose --profile prod down
```

Or via Makefile (Git Bash / WSL / Linux):

```bash
export SESSION_SECRET=...
make up-prod
make health
make logs-prod
make down-prod
```

Windows PowerShell:

```powershell
$env:SESSION_SECRET = "your-long-secret"
.\scripts\up-prod.ps1
```

Volumes: `postgres_data` (DB), `uploads_data` (property media). Redis is included in the `prod` profile for optional cache/Celery.

## 4. Health checks

| Path | Purpose |
|------|---------|
| `GET /healthz` | Process up (liveness) |
| `GET /readyz` | DB reachable (readiness) |

Wire these into load balancers / Kubernetes probes.

## 5. CSS workflow

| Mode | How |
|------|-----|
| Production | `npm run build:css` → `static/css/tailwind-ph.css`; `USE_TAILWIND_CDN=0` |
| Local UI hack | `USE_TAILWIND_CDN=1` loads Tailwind CDN (not for prod) |
| Watch | `npm run watch:css` while editing templates |

After template class changes, re-run `npm run build:css` before shipping.

## 6. Security checklist

- [ ] `SESSION_SECRET` is unique and long (production refuses default secret)
- [ ] HTTPS terminated (cookie `Secure` + HSTS headers when `FLASK_ENV=production`)
- [ ] `ENABLE_CSRF=1` for form posts
- [ ] Admin routes require auth (`/admin/*`)
- [ ] No API keys in git; rotate leaked keys
- [ ] Review CSP if you add new third-party scripts
- [ ] Backups for `DATABASE_URL` / upload volume (`static/uploads`)

## 7. Post-deploy smoke

```bash
curl -fsS https://your-host/healthz
curl -fsS https://your-host/readyz
curl -fsSI https://your-host/ | head
# Browser: login → dashboard → properties → map → recommendations
```

## 8. Rollback

1. Redeploy previous app image / git tag  
2. `flask db downgrade -1` only if the failed release added a migration you must reverse  
3. Restore DB snapshot if data migrations were destructive  

## 9. CI (GitHub Actions)

Workflow: `.github/workflows/tests.yml`

| Job | What it does |
|-----|----------------|
| **css** | `npm ci` + `npm run build:css`, asserts `tailwind-ph.css` exists |
| **lint** | Ruff on core packages |
| **core-tests** | Platinum Heritage UI + smoke + forms/SMS (must pass) |
| **full-tests** | Entire pytest suite (informational; `continue-on-error`) |

Local mirror:

```bash
npm run build:css
pytest -q tests/test_platinum_heritage_ui.py tests/test_app_smoke.py tests/test_simple.py
```

## Feature surface (reference)

| Area | Route examples |
|------|----------------|
| CRM | `/`, `/properties`, `/agents`, `/customers`, `/deals`, `/tasks` |
| Insights | `/market`, `/compare`, `/calculators` |
| Outreach | `/messaging`, `/sms` |
| Docs / kiosk | `/contracts`, `/kiosk` |
| Map | `/properties/map` |

# Platinum Heritage CRM (gptvli)

Flask CRM for properties, agents, customers, deals, and tasks — with AI recommendations, multi-parameter hybrid scoring, and optional background rematch.

> **Product path (use this):** Flask + SQLAlchemy + Jinja2 + Tailwind (Platinum Heritage shell).  
> **Architecture:** [docs/adr-001-architecture.md](docs/adr-001-architecture.md) · [docs/architecture.md](docs/architecture.md) · [docs/PRODUCTION.md](docs/PRODUCTION.md)

---

## Product path vs experimental stack

| Track | What | Status |
|-------|------|--------|
| **A — Flask CRM** | Listings, clients, deals, tasks, recs, map, media, PH UI | **Primary product — ship this** |
| **B — Matching microservices** | Neo4j + `api/` + `matcher/` + `ingestor/` + `chatbot/` | **Experimental — do not build or run unless you have an explicit graph-matching product need** |

Track B is documented only for experiments: [docs/matching-platform.md](docs/matching-platform.md).  
It is **not** required for recommendations, rematch, or day-to-day CRM. Do **not** start Neo4j/matcher for a login page or list CRUD.

Long-term (only if product requires it): optional HTTP adapter Flask → matcher — **not started**. Prefer finishing Track A.

---

## Features (current product)

- Property / agent / customer / deal / task CRUD
- Iranian listing fields (sale/rent, rahn, ejare) where modeled
- Platinum Heritage UI shell (sidebar, modals, tokens, Material Symbols)
- AI form assist + property recommendations (Gemini / configured LLM)
- Hybrid search + vector embeddings (`services/vector_service`)
- **Multi-parameter match scoring:** semantic, budget, location, type, rooms, amenities, size
- **Score mix UI** on recommendations (per-property bars + reasons)
- **Client match profile** on recommendations + **View Profile** on customers (prefs + completeness)
- Always-on rematch path (RematchQueue + Celery beat defaults ~60s; needs Redis + worker)
- Agent notifications for new / improved high matches (deduped)
- Map, media gallery, market/compare/ROI/messaging/SMS/contracts/kiosk routes (PH templates)
- Optional production packaging: Docker prod profile, healthz/readyz, CSRF defaults

## What’s done recently (Track A)

| Area | Delivered |
|------|-----------|
| UI migration | PH templates for core CRM pages; branch `005-template-replacement` |
| Recommendations | Score mix breakdown UI; preference completeness; save & re-rank |
| Customers | View Profile modal with full match parameters + edit/save |
| Matching engine | Richer hard filters + hybrid weights; dismissed-match exclusion |
| Always-on | Faster rematch queue drain; separate property/customer cycles; notify on new/improved scores |
| Ops | `.env.example` matcher knobs; `docs/PRODUCTION.md`; Docker multi-stage |

**Supported run paths:** root app (`python main.py`) and Docker Compose prod profile (`docs/PRODUCTION.md`).
A local `platinum-heritage-runnable/` tree is **not** maintained as a second source of truth (ignored if present).

---

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) recommended (or pip)
- Optional: Redis + Celery for always-on rematch / digests
- Optional: `GEMINI_API_KEY` (or provider keys) for AI embeddings/reasoning
- Optional: Node 18+ only if rebuilding Tailwind CSS (`npm run build:css`)

## Quick start (CRM)

```bash
# Install
uv sync
# or: python -m pip install -r requirements.txt

# Config (never commit secrets)
cp .env.example .env
# Set SESSION_SECRET (and GEMINI_API_KEY for full AI)

# Run web app
python main.py
# → http://127.0.0.1:55555
```

### Always-on rematch (optional but recommended)

```bash
# Terminal 1 — Redis
docker compose --profile crm up -d redis
# REDIS_URL=redis://localhost:6379/0 in .env

# Terminal 2 — worker
celery -A celery_app.celery_app worker -l info
# or: python worker.py

# Terminal 3 — beat (schedules rematch queue / matching)
celery -A celery_app.celery_app beat -l info
```

Defaults (overridable in `.env`): rematch queue ~every **60s**, full matching sweep ~**15 min**.  
See matching / notification knobs in `.env.example`.

### Optional Redis only

```bash
docker compose --profile crm up -d redis
```

---

## Project layout (core)

| Path | Role |
|------|------|
| `app.py` / `main.py` | Flask app factory and dev entry (port **55555**) |
| `views/` | HTTP blueprints |
| `services/` | Business logic (canonical DB / AI / vector / geo) |
| `background_matcher.py` | Property–customer matching + agent alerts |
| `sqlalchemy_models.py` | ORM models |
| `templates/` | Jinja UI (`components/` shared shell) |
| `worker.py` / `celery_app.py` | Background jobs |
| `tests/` | pytest suite |
| `specs/005-template-replacement/` | UI replacement notes / status |
| `docs/PRODUCTION.md` | Production runbook |

Root `database_service.py` / `gemini_service.py` are **compatibility shims** re-exporting `services.*`. Prefer `from services...`.

**Ignore for product work unless explicitly needed:** `api/`, `matcher/`, `ingestor/`, `chatbot/`, `stitch_kpi_performance_dashboard/`, agent tooling dirs, `graphify-out/`.

---

## Environment (common)

| Variable | Purpose |
|----------|---------|
| `SESSION_SECRET` | Flask secret (required in production) |
| `DATABASE_URL` | SQLite locally; Postgres in production |
| `GEMINI_API_KEY` | Gemini LLM / embeddings |
| `LLM_PROVIDER` | `gemini` (default) or `kie` |
| `REDIS_URL` | Celery / cache / rate limit backend |
| `ENABLE_CSRF` | `1` to enable Flask-WTF CSRF |
| `USE_TAILWIND_CDN` | `1` for local CDN Tailwind; `0` use built CSS |
| `REMATCH_QUEUE_INTERVAL_SECONDS` | Always-on queue drain (default `60`) |
| `MATCHING_INTERVAL_MINUTES` | Full match sweep (default `15`) |
| `MATCHER_*` / `*_WEIGHT` | Score thresholds and hybrid weights |

Full flags: `docs/architecture.md` and `.env.example`.

---

## Tests

```bash
python -m pytest tests/test_app_smoke.py tests/test_platinum_heritage_ui.py tests/test_always_on_matching.py tests/test_match_parameters.py -q
```

---

## Docker

- **CRM infra (Redis):** `docker compose --profile crm up -d`
- **Production-style web + Postgres:** see `docs/PRODUCTION.md` (`--profile prod`)
- **Experimental matching stack:** `docker compose --profile matching up -d`  
  **Do not use for normal development.** Details: [docs/matching-platform.md](docs/matching-platform.md)

---

## Next (real product backlog)

Prioritized for the **Flask CRM only** — not Track B:

1. ~~**Always-on local stack**~~ — `scripts/dev-always-on.ps1`, `make redis-up` / `worker` / `beat` / `always-on`  
2. ~~**Recs dismiss + empty guidance**~~ — dismiss match API + card action; empty-state prefs guidance  
3. ~~**Client card completeness**~~ — Prefs % badge on `/customers` cards  
4. ~~**Match alert bell**~~ — shell inbox via `/api/notifications/inbox`  
5. ~~**Production hardening checklist**~~ — fail-closed migrations, required secrets, `/readyz`, Postgres CI  
6. **Housekeeping** — after audit, confirm delete of `templates/_archive/` (optional); Stitch exports stay out of Docker  
7. **Only if product requires graph matching later** — design HTTP adapter Flask → matcher; until then leave Track B alone  

**Explicitly not next (unless product asks):** Neo4j rollout, rewriting CRM in Next.js, promoting `api/`/`matcher/` to default onboarding.

---

## Development notes

- UI work branch: `005-template-replacement`
- Optional code graph: `graphify-out/` — `graphify update .` (dev tooling only)
- Do not commit `.env`, API keys, DB files, `node_modules`, or large Stitch PNG dumps

## License / status

Internal Platinum Heritage CRM. **Ship Track A.** Matching microservices remain experimental and are not required to run the product.

# Real Estate CRM (gptvli)

Flask CRM for properties, agents, customers, deals, and tasks — with AI recommendations, embeddings, and optional background matching.

> **Product path:** Flask + SQLAlchemy + Jinja (this README).  
> **Experimental matching stack** (Neo4j / Next API / ingestor / matcher / chatbot): see [docs/matching-platform.md](docs/matching-platform.md).  
> **Architecture decision:** [docs/adr-001-architecture.md](docs/adr-001-architecture.md).  
> **Runtime details:** [docs/architecture.md](docs/architecture.md).

## Features

- Property / agent / customer / deal / task CRUD
- Iranian listing fields (sale/rent, rahn, ejare) where modeled
- AI form assist and property recommendations (Gemini or configured LLM provider)
- Hybrid search + vector embeddings
- Celery worker for rematch queue, digests, and automations
- Stitch-based UI shell (`templates/base.html` + shared components)

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) recommended (or pip)
- Optional: Redis (Celery / cache / rate limits)
- Optional: `GEMINI_API_KEY` in `.env` for AI features

## Quick start (CRM)

```bash
# Install
uv sync
# or: python -m pip install -r requirements.txt

# Config (never commit secrets)
cp .env.example .env
# Set SESSION_SECRET and GEMINI_API_KEY in .env

# Run web app
python main.py
# → http://127.0.0.1:5000 (or 0.0.0.0:5000 depending on main.py)

# Optional worker (separate terminal)
python worker.py
```

### Optional Redis (CRM profile)

```bash
docker compose --profile crm up -d redis
# Set REDIS_URL=redis://localhost:6379 in .env if needed
```

## Project layout (core)

| Path | Role |
|------|------|
| `app.py` / `main.py` | Flask app factory and dev entry |
| `views/` | HTTP blueprints |
| `services/` | Business logic (canonical DB/AI services) |
| `sqlalchemy_models.py` | ORM models |
| `templates/` | Jinja UI (`components/` shared shell) |
| `worker.py` / `celery_app.py` | Background jobs |
| `tests/` | pytest suite |
| `specs/005-template-replacement/` | Active UI replacement feature |

Root `database_service.py` / `gemini_service.py` are **compatibility shims** re-exporting `services.*`. Prefer importing from `services/`.

## Environment

| Variable | Purpose |
|----------|---------|
| `SESSION_SECRET` | Flask secret (required in production) |
| `DATABASE_URL` | Default SQLite locally; Postgres in production |
| `GEMINI_API_KEY` | Gemini LLM / embeddings |
| `LLM_PROVIDER` | `gemini` (default) or `kie` |
| `REDIS_URL` | Celery / cache / rate limit backend |
| `ENABLE_CSRF` | Set `1` to enable Flask-WTF CSRF |

See `docs/architecture.md` for the full flag list.

## Tests

```bash
python -m pytest tests/test_app_smoke.py tests/test_dashboard_template.py -q
```

## Docker

- **CRM infrastructure only:** `docker compose --profile crm up -d`
- **Experimental matching stack:** `docker compose --profile matching up -d`  
  Details: [docs/matching-platform.md](docs/matching-platform.md)

## Development notes

- Branch work for UI shell: `005-template-replacement`
- Knowledge graph (optional): `graphify-out/` — refresh with `graphify update .`
- Do not commit `.env`, API keys, DB files, or `node_modules`

## License / status

Internal / in-progress CRM. Matching microservices are experimental and not required to run the Flask product.

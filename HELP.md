# 🏠 Real Estate CRM (gptvli) — Setup & Run Guide

## Prerequisites

- **Python 3.13+**
- **Redis** (optional — for rate limiting, caching, and Celery background tasks)
- **Maskan Scraper** (separate project, must be running for auto-sync)

---

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file (see Environment Variables below)
copy .env.example .env       # or create manually

# 4. Run the app
python app.py
```

The app starts at **http://127.0.0.1:5000**

---

## Environment Variables

Create a `.env` file in the project root:

```env
# ── Required ──
SESSION_SECRET=your-strong-secret-key-here

# ── Database ──
# Leave empty for SQLite (default: sqlite:///real_estate_crm.db)
# For PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/crm_db

# ── Maskan Scraper (Auto-Sync) ──
MASKAN_LIVE_API_BASE_URL=http://localhost:8000

# ── AI / LLM Providers ──
KIE_API_KEY=your-kie-api-key
KIE_BASE_URL=https://api.kie.ai          # default, optional
GEMINI_API_KEY=your-gemini-api-key        # for AI extraction & copilot

# ── Redis (optional, defaults to localhost:6379) ──
REDIS_URL=redis://localhost:6379/0

# ── Auth (set to 0 to disable login during development) ──
AUTH_DEFAULT_DENY_ENABLED=1

# ── CSRF (set to 0 to disable during API testing) ──
ENABLE_CSRF=1
```

---

## Running Modes

### Development Server
```bash
python app.py
# Runs on http://127.0.0.1:5000 with debug=True
```

### Production (Gunicorn)
```bash
gunicorn app:app --bind 0.0.0.0:5000 --workers 4
```

### Celery Worker (background tasks)
```bash
celery -A celery_app worker --loglevel=info
```

---

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_maskan_live_service.py -v
python -m pytest tests/test_sync_integration.py -v

# With coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

---

## Project Structure

```
gptvli/
├── app.py                  # App factory & entry point
├── database.py             # DB init, SQLite schema patches
├── sqlalchemy_models.py    # All ORM models
├── celery_app.py           # Celery configuration
├── extensions.py           # Flask extensions (limiter, cache)
├── requirements.txt        # Python dependencies
│
├── services/
│   ├── database_service.py        # CRUD operations
│   ├── maskan_live_service.py     # Scraper sync engine
│   ├── search_service.py          # Property search
│   ├── favorites_service.py       # User favorites
│   └── llm/providers/
│       ├── kie_provider.py        # Kie.ai LLM
│       └── gemini_provider.py     # Google Gemini LLM
│
├── views/
│   ├── main.py             # Dashboard, sync triggers
│   ├── properties.py       # Property CRUD + API
│   ├── agents.py           # Agent management
│   ├── customers.py        # Customer management
│   ├── deals.py            # Deal pipeline
│   ├── tasks.py            # Task management
│   └── auth.py             # Authentication
│
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS, JS, images
└── tests/                  # Pytest test suite
```

---

## Key API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Dashboard |
| `/properties` | GET | Property list |
| `/properties/<id>/detail` | GET | Property detail page |
| `/api/properties/<id>/changelog` | GET | Field change history |
| `/api/properties/<id>/rollback` | POST | Rollback a field |
| `/api/sync/status` | GET | Scraper sync status |

---

## Maskan Scraper Integration

The scraper is a **separate project** that must be running. Set its URL:

```env
MASKAN_LIVE_API_BASE_URL=http://localhost:8000
```

Sync is triggered from the admin dashboard or via API. The CRM calls:
- `GET /api/v2/integrations/gptvli/properties/changes` — incremental sync
- `POST /api/v2/properties/search` — property search

---

## Database

- **Development**: SQLite (`real_estate_crm.db`, auto-created)
- **Production**: PostgreSQL (set `DATABASE_URL`)

The app auto-patches missing SQLite columns on startup. For PostgreSQL, use Flask-Migrate:

```bash
flask db upgrade
```

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError` | Activate venv: `venv\Scripts\activate` |
| `no such table: properties` | Delete `real_estate_crm.db` and restart |
| Sync not working | Check `MASKAN_LIVE_API_BASE_URL` and scraper is running |
| Rate limit errors | Install Redis or set `RATELIMIT_STORAGE_URI=memory://` |
| CSRF errors in API testing | Set `ENABLE_CSRF=0` in `.env` |

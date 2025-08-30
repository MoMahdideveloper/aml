# Repository Guidelines

## Project Structure & Module Organization
- `app.py`: Flask app factory/bootstrap and DB init.
- `routes.py`: HTTP routes and view handlers.
- `database.py`: SQLAlchemy/Flask‑Migrate setup.
- `sqlalchemy_models.py` and `models.py`: ORM models and related helpers.
- `templates/` and `static/`: Jinja2 HTML and assets.
- `migrations/`: Alembic migration scripts (managed by Flask‑Migrate).
- `chroma_db/` and `vector_*`: Vector store setup and services.
- `gemini_service.py`: Google Generative AI integration.
- `main.py`: Local development entry point.

## Build, Test, and Development Commands
- Install (uv preferred): `uv sync`
  - Pip alternative: `python -m pip install -U flask flask-sqlalchemy flask-migrate pydantic sqlalchemy chromadb google-genai gunicorn numpy scikit-learn email-validator sift-stack-py psycopg2-binary`
- Run dev server: `python main.py` (serves on `http://0.0.0.0:5000` with debug).
- DB migrations: set `FLASK_APP=app.py` then `flask db migrate -m "msg"` and `flask db upgrade`.
- Production (example): `gunicorn -w 2 -b 0.0.0.0:8000 main:app`.

## Coding Style & Naming Conventions
- Python 3.11+, PEP 8, 4‑space indentation, UTF‑8.
- Files and functions: `snake_case`; classes/ORM models: `PascalCase`; constants: `UPPER_SNAKE`.
- Keep routes in `routes.py`, templates under `templates/` with matching names (e.g., `properties.html`).
- Prefer type hints and small, single‑purpose functions.

## Testing Guidelines
- Currently no test suite in the repo. Add tests under `tests/` using `pytest` and Flask’s test client.
- Example: name files `test_<module>.py`; aim for coverage on routes, services, and DB ops.
- Run: `pytest -q` (after installing `pytest`).

## Commit & Pull Request Guidelines
- Commits: imperative mood, short subject (≤72 chars), optional scope, explain the “why” in the body.
- Reference issues: `Fixes #123` or `Refs #123`.
- PRs: clear description, steps to verify, screenshots for UI changes, migration notes if DB schema changes, and linked issue.

## Security & Configuration Tips
- Required env vars: `SESSION_SECRET` (use a strong value), `DATABASE_URL` for production; optional provider keys for `gemini_service.py` (e.g., `GOOGLE_API_KEY`).
- Do not commit secrets or local DB files; prefer a `.env` and environment‑specific configs.
- For local SQLite, default is `sqlite:///real_estate_crm.db`; use Postgres in production via `DATABASE_URL`.


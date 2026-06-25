# SQLite to Postgres + pgvector Migration

## Goal
Move from local SQLite-only operation to managed Postgres with vector search support.

## 1. Provision Postgres
1. Create a Postgres database (v14+ recommended).
2. Set `DATABASE_URL`, for example:
   - `postgresql+psycopg://user:password@host:5432/gptvli`

## 2. Enable pgvector
Run once on the target database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 3. Apply Migrations
From project root:

```bash
set FLASK_APP=app.py
flask db upgrade
```

This creates:
- `property_embeddings`
- `matching_job_runs`
- `rematch_queue`
- `automation_rules`
- `automation_audit_log`

On Postgres, migration also adds:
- `property_embeddings.embedding_vector vector(768)`
- `ix_property_embeddings_vector_hnsw` index

## 4. Configure Runtime
Set environment variables:

```bash
SESSION_SECRET=<strong-random-value>
LLM_PROVIDER=gemini
EMBEDDING_PROVIDER=gemini
EMBEDDING_DIM=768
VECTOR_DISTANCE=cosine
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}
CACHE_REDIS_URL=${REDIS_URL}
RATELIMIT_STORAGE_URI=${REDIS_URL}
AUTH_DEFAULT_DENY_ENABLED=1
```

Run worker processes separately:

```bash
python worker.py worker
python worker.py beat
```

## 5. Backfill Embeddings
Use existing initializer flow:

```bash
python migrate_embeddings.py
```

Or run a one-off script that calls:
- `vector_init.ensure_vector_database_ready()`

## 6. Validation Checklist
- `python -c "import app; print('ok')"` succeeds.
- `GET /api/vector/status` returns `database_ready` once indexed.
- Celery worker logs show task registration and Celery beat logs show periodic dispatch.
- Recommendation endpoints return ranked results.

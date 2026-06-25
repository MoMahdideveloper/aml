# Runtime Architecture

## Processes
- Web process (`main.py` -> `app.py`)
  - Serves HTTP/Jinja/API requests.
  - Registers event handlers.
  - Never runs scheduled jobs.
- Worker process (`worker.py`)
  - Runs Celery worker or Celery beat.
  - Executes rematch queue processing, periodic matching, cleanup, digests, and overdue-task automation.

## Request and Matching Flow
1. User/API request enters blueprint in `views/*`.
2. Blueprint calls service layer in `services/*`.
3. Recommendation flow:
   - `services/search_service.py` (hybrid ranking)
   - `services/vector_service.py` (embedding + semantic scores)
   - `services/gemini_service.py` (reasoning for top-N results)
4. DB model change events enqueue lightweight rematch records (`rematch_queue`).
5. Worker dequeues and executes matching cycles in batches.

## AI/Search Stack
- LLM: provider interface in `services/llm/providers/base.py`, default Gemini provider.
- Embeddings: provider interface in `services/embeddings/providers/base.py`, default Gemini embedding provider.
- Vector storage:
  - Cross-DB fallback: JSON embedding payload in `property_embeddings.embedding_data`.
  - Postgres: optional `embedding_vector vector(768)` with HNSW index.

## Key Environment Flags
- `REDIS_URL`: shared Redis endpoint.
- `CELERY_BROKER_URL`: defaults to `REDIS_URL`.
- `CELERY_RESULT_BACKEND`: defaults to `REDIS_URL`.
- `CACHE_REDIS_URL`: defaults to `REDIS_URL`.
- `RATELIMIT_STORAGE_URI`: defaults to `REDIS_URL`.
- `AUTH_DEFAULT_DENY_ENABLED`: default `1`.
- `LLM_PROVIDER`: default `gemini` (`gemini` or `kie`).
- `KIE_API_KEY`: required when `LLM_PROVIDER=kie`.
- `KIE_MODEL`: default `gemini-2.5-flash`.
- `KIE_BASE_URL`: default `https://api.kie.ai`.
- `KIE_CHAT_COMPLETIONS_URL`: optional full override for chat endpoint.
- `EMBEDDING_PROVIDER`: default `gemini`.
- `EMBEDDING_DIM`: default `768`.
- `VECTOR_DISTANCE`: `cosine` (default), `l2`, `ip`.

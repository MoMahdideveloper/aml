# ADR-001: Flask CRM is the product; matching microservices are experimental

## Status

Accepted (2026-07-09)

## Context

The repository contained two parallel narratives:

1. **Track A — Real Estate CRM:** Flask app factory, SQLAlchemy models, Jinja UI, Celery worker, Gemini embeddings/recommendations (`docs/architecture.md`, `PRD.md`).
2. **Track B — Matching platform:** Docker Compose Neo4j/Redis plus `api/`, `matcher/`, `ingestor/`, `chatbot/` (`README.md` historically described only this stack).

Running both as “the app” doubles operational cost, confuses onboarding, and causes agents to start Neo4j for a login page.

Recent work (`005-template-replacement`, service shims, shared UI shell) reinforces Track A as the shippable product.

## Decision

1. **Primary product = Track A (Flask CRM).** Day-to-day run: `uv sync` → `.env` → `python main.py` (+ optional `worker.py` and Redis).
2. **Track B remains in-repo as experimental.** Documented in `docs/matching-platform.md`. Not required for CRM features.
3. **Root README documents Track A first.** Microservices details live under `docs/`.
4. **Compose uses profiles:** `crm` (Redis) vs `matching` (Neo4j + Redis + microservices).
5. **Canonical Python services live under `services/`.** Root `database_service.py` / `gemini_service.py` are re-export shims only.

## Consequences

### Positive

- Clear onboarding and agent context
- Smaller default runtime (no Neo4j for basic CRM)
- Single source of truth for DB/AI modules

### Negative / trade-offs

- Track B may lag or diverge until an explicit product requirement needs Neo4j
- README must stay updated so Track B does not re-become the default story

### Follow-ups

- Wire list/detail navigation consistently on the CRM shell
- Optional: HTTP adapter from Flask → matcher if graph matching becomes required
- Optional: move experimental trees under `experiments/` later

## Related

- [architecture.md](architecture.md)
- [matching-platform.md](matching-platform.md)
- [../README.md](../README.md)

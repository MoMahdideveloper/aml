# Experimental matching platform (Track B)

This document describes the **optional** microservices stack under `api/`, `matcher/`, `ingestor/`, and `chatbot/`. It is **not** required to run the Flask Real Estate CRM (Track A).

## When to use this stack

- Multi-hop graph traversal over property/customer relationships in **Neo4j**
- Separate Next.js API + FastAPI chatbot + BullMQ workers
- Horizontal service isolation experiments

For day-to-day CRM work (listings, deals, AI recommendations inside Flask), use the main [README.md](../README.md) instead.

## Services

| Service | Path | Default port | Role |
|---------|------|--------------|------|
| Neo4j | compose | 7474 / 7687 | Graph store |
| Redis | compose | 6379 | Queue / cache |
| Ingestor | `ingestor/` | 8000 | Ingest + embeddings |
| Matcher | `matcher/` | 8001 | Match workers |
| API | `api/` | 3000 | Next.js HTTP API |
| Chatbot | `chatbot/` | 8002 | RAG chat |

## Start

Requires Docker, and typically `GEMINI_API_KEY` in the environment for ingestor/chatbot.

```bash
# From repo root
docker compose --profile matching up --build
```

Health examples (when implemented):

- Ingestor: `http://localhost:8000/health`
- Matcher: `http://localhost:8001/health`
- API: `http://localhost:3000/api/health`
- Chatbot: `http://localhost:8002/health`
- Neo4j Browser: `http://localhost:7474`

Default Neo4j auth in compose is development-only (`neo4j/changemeplease`). Change before any shared or production use.

## Relationship to Flask CRM

| Concern | Track A (CRM) | Track B (this doc) |
|---------|---------------|--------------------|
| UI | Jinja templates | Separate clients / chatbot |
| Primary DB | SQLAlchemy (SQLite/Postgres) | Neo4j (+ Redis) |
| Matching | `services/search_service`, vectors, Celery rematch | Matcher service + graph traversal |
| Product status | **Primary** | Experimental |

Long-term integration, if needed: keep Flask as BFF/UI; call matcher via HTTP adapters from `services/`; do not rebuild full CRUD in Next.js until the CRM is stable.

## Ops notes

- `api/node_modules` and `matcher/node_modules` are large; do not commit them.
- Prefer `docker compose --profile matching down` when not experimenting to free RAM.
- Graphify and agent tooling should ignore these trees for code graphs when possible.

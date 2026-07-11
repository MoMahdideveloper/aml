# CRM intelligence — operator guide

Track A only. All intelligence flags default **off** (except global search) so production stays safe until you opt in.

## Staging enablement

See **`docs/INTELLIGENCE_STAGING_CHECKLIST.md`** for a step-by-step go-live sequence (shadow hybrid, vocab, context, rollback).

## Admin UI toggles

Use **`/admin/intelligence`** (admin auth) to turn features on/off without redeploying.


- First DB row is **seeded from environment** variables.
- After that, **admin UI values win** (runtime `app.config` is updated on save).
- Vocabulary term management remains at `/admin/vocab`.


## Migrations

```bash
# From repo root with FLASK_APP=app.py
flask db upgrade
# Heads used by this epic:
#   r3s4t5u6v7w8  vocab tables (PR1)
#   s4t5u6v7w8x9  relationship_edges (PR4)
#   t5u6v7w8x9y0  vocab_occurrences + edge confidence (v2)
flask db current
```


SQLite and Postgres both supported for these tables.

## Feature flags (recommended rollout order)

| Order | Flag | Default | What turns on |
|------:|------|---------|----------------|
| 1 | `ENABLE_VOCAB_ENRICHMENT` | `0` | Property search synonym/replacement expand |
| 2 | `ENABLE_VOCAB_OCCURRENCES` | `0` | Extract/index term occurrences (Celery reindex) |
| 3 | `ENABLE_CUSTOMER_NL_FILTERS` | `0` | Customer structured NL (beds/budget/type/location); admin toggle `customer_nl_filters` |
| 4 | `ENABLE_HYBRID_SEARCH` | `0` | Full `/search` property hybrid re-rank + evidence |
| 5 | `ENABLE_AI_CONTEXT` | `0` | `/api/context/...` (customer/property/deal/task/agent) |
| 6 | `ENABLE_AI_ANSWER` | `0` | Grounded answers `POST .../answer` (needs context ON) |
| 7 | `ENABLE_DERIVED_EDGES` | `0` | Related panel + `/api/related/...` |
| 8 | `ENABLE_SEARCH_SHADOW` | `0` | Hybrid compute, keyword display order |
| 9 | `ENABLE_DESCRIPTION_SEARCH` | `0` | Keyword search in property description |
| 10 | `ENABLE_NL_QUERY_PARSE` | `0` | Optional LLM soft-constraint parse (fail-open) |
| 11 | `ENABLE_ACTIVITY_SEARCH` | `0` | Interaction metadata search (`scope=activities`; type/outcome/id only) |

Check **Property embedding coverage** on `/admin/intelligence` before enabling hybrid live.




Optional: `AI_CONTEXT_MAX_CHARS=8000`.

### Suggested staging sequence
1. Deploy code + migrate with **all flags 0**. Smoke CRM as usual.  
2. Enable **vocab** only; seed a few EN synonyms in `/admin/vocab`; test property search.  
3. Enable **hybrid**; ensure property embeddings exist for semantic path (else keyword + degraded chips).  
4. Enable **AI context**; call one customer/property/deal packet; confirm no note bodies.  
5. Enable **derived edges**; open Customer 360 / property Related; optional `POST .../rebuild`.  

## Admin surfaces

| Path | Auth | Notes |
|------|------|--------|
| `/admin/vocab` | Admin session (`require_admin_auth`) | CRUD always available; expand only if vocab flag on |
| `/search` | Staff session | Hybrid when hybrid flag on |
| `/api/context/<type>/<id>` | Staff session | 404 if context flag off |
| `/api/related/<type>/<id>` | Staff session | 404 if edges flag off |
| Customer 360 | Staff | Related + AI context links when flags on |

## Privacy checklist
- Search/hybrid logs: duration, counts, flags — **never** raw `q`.  
- Context logs: entity ids + char counts — **never** packet body.  
- Edges `evidence_json`: ids/status only — no free-text notes.  

## Failure / fallback
| Subsystem | On failure |
|-----------|------------|
| Vocab lexicon | Unexpanded keyword search |
| Embeddings / hybrid semantic | Keyword-only + `hybrid.degraded` |
| Context disabled | HTTP 404 |
| Edge rebuild empty | Neighbors `[]`; API still 200 after rebuild attempt |

## Rollback
1. Set flags to `0` (instant behavior off).  
2. Optional: `flask db downgrade` only if you must drop tables (coord with backup).  
3. Vocab/admin data is soft-archive friendly — no need to wipe terms.  

## Non-goals (do not enable by accident)
Neo4j as required path, auto-synonym from embeddings, searching interaction note bodies, defaulting flags to `1` in production without a deliberate decision.

## Related contracts
- `docs/CRM_INTELLIGENCE_CONTRACT.md`  
- `docs/VOCAB_CONTRACT.md`  
- `docs/AI_CONTEXT_CONTRACT.md`  
- `docs/RELATIONSHIP_EDGES_CONTRACT.md`  
- `docs/SEARCH_CONTRACT.md`  

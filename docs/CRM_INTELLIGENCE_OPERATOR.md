# CRM intelligence — operator guide

Track A only. All intelligence flags default **off** so production stays safe until you opt in.

## Migrations

```bash
# From repo root with FLASK_APP=app.py
flask db upgrade
# Heads used by this epic:
#   r3s4t5u6v7w8  vocab tables (PR1)
#   s4t5u6v7w8x9  relationship_edges (PR4)
flask db current
```

SQLite and Postgres both supported for these tables.

## Feature flags (recommended rollout order)

| Order | Flag | Default | What turns on |
|------:|------|---------|----------------|
| 1 | `ENABLE_VOCAB_ENRICHMENT` | `0` | Property search synonym/replacement expand |
| 2 | `ENABLE_HYBRID_SEARCH` | `0` | Full `/search` property hybrid re-rank + constraint filters |
| 3 | `ENABLE_AI_CONTEXT` | `0` | `/api/context/...` + Customer 360 JSON link |
| 4 | `ENABLE_DERIVED_EDGES` | `0` | Related panel + `/api/related/...` |

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

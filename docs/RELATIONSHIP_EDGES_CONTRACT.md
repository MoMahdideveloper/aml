# Relationship edges (Track A)

## Purpose
Lightweight **SQL** graph of CRM relationships for “why related” explainability.
Not Neo4j / Track B.

## Flag
`ENABLE_DERIVED_EDGES` — default `0`. When off, related APIs return 404.

## Edge types (deterministic from FKs)

| edge_type | Meaning |
|-----------|---------|
| `customer_deal` | Customer ↔ Deal |
| `deal_property` | Deal ↔ Property |
| `customer_agent` | via deal.agent_id |
| `property_agent` | property.agent_id |
| `deal_agent` | deal.agent_id |
| `task_relates_to` | task source entity / agent |
| `entity_mentions_concept` | vocab occurrence → term_id as concept |

## API
- `GET /api/related/<entity_type>/<id>?depth=1` — neighbors (rebuild-if-empty)
- `POST /api/related/<entity_type>/<id>/rebuild` — force rebuild

Auth: session staff. Soft-deleted entities: not_found on rebuild.

## Rebuild
Idempotent: delete edges touching entity (our edge types), recreate from live FKs.
`source_run_id` stamps the rebuild batch.

## Evidence
`evidence_json` may hold small ids/status only — **no** note bodies / free text.

## UI
- Customer 360: **Related** panel when flag on  
- Property detail: **Related (CRM graph)** panel when flag on  

## Non-goals
Pathfinding libraries, co-deal mining, embedding similarity edges, Neo4j sync.

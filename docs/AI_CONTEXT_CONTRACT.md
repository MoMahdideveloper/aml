# AI context packets (Track A)

## Purpose
Build **complete, allowlisted** context packets for CRM entities so agents/tools can reason without dumping raw PII notes or secrets.

## Flag
`ENABLE_AI_CONTEXT` — default `0`. When off, `/api/context/...` returns **404**.

## Endpoint
`GET /api/context/<entity_type>/<id>?purpose=match|brief|search_explain`

- Auth: session staff (`user_id`) required (401 if anonymous).
- Soft-deleted entities: 404.
- entity_type: `customer`|`property`|`deal` (plurals accepted).

## Field policy

| Include | Exclude |
|---------|---------|
| Structured CRM fields with provenance | `preferences` free text |
| Truncated property description/features | Deal `notes` |
| Interaction **type / outcome / dates** only | Interaction `body` / `subject` |
| Deal stage history summary | Embeddings, storage keys, secrets |
| Budget bands, status, type | Passwords, document binary |

Each scalar field is wrapped: `{ "value", "source", "as_of" }`.

## Budgets
`AI_CONTEXT_MAX_CHARS` (default 8000). Oversized packets drop lower-priority sections (`stage_history` → `timeline` → `deals` → description).

## Telemetry
Log entity_type, entity_id, purpose, char_count. **Never** log packet body or free-text content.

## Non-goals
LLM generation of the packet, auto-including note bodies, multi-tenant row ACLs beyond global staff model.

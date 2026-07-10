# Unified CRM search contract (Track A)

## Scope
Customers, properties, deals, agents, tasks — SQLAlchemy only (no Elasticsearch/vector).

## Query rules
| Rule | Value |
|------|--------|
| Min length | 2 (except pure numeric exact ID) |
| Max length | 100 |
| Normalize | trim, collapse whitespace; case-insensitive match |
| Ranking | (1) exact ID (2) exact identifier (3) prefix (4) contains |
| Sort tie-break | entity id ascending |
| Fuzzy | **none** (v1) |
| Empty query | no free-text hits; filters-only allowed on full page |
| Malformed | 400 JSON or flash + empty results |

## Limits
- Autocomplete: **5** results per entity group, **20** total
- Full page: **20** per entity page, pagination via `page`
- Max scopes per request: all 5 entities

## Permissions
Authenticated CRM staff (session `user_id`) with global read model (same as list pages).  
Anonymous denied. Soft-deleted rows always excluded.  
v1 does **not** multi-tenant filter by owner; document if product changes.

## Telemetry
Log duration, counts, zero-result flag, failure category. **Never log raw query text.**

## Feature flag
`ENABLE_GLOBAL_SEARCH` — default `1`. Set `0` to hide shell control and deny routes.
Cleanup: remove flag after one stable release cycle.

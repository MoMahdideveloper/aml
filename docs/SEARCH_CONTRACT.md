# Unified CRM search contract (Track A)

## Scope
Customers, properties, deals, agents, tasks — SQLAlchemy only (no Elasticsearch/vector).  
Optional scope **`activities`** (customer interactions) when `ENABLE_ACTIVITY_SEARCH=1` — **not** included in default “all scopes”.

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

## Vocabulary expand (optional)
`ENABLE_VOCAB_ENRICHMENT` — default `0`. When `1`, **property** free-text search may OR-match up to 8 expanded keys (synonyms / replacements). See `docs/VOCAB_CONTRACT.md`. Other entity scopes unchanged. Flag off = legacy keyword-only behavior.

## Hybrid ranking (optional)
`ENABLE_HYBRID_SEARCH` — default `0`. When `1`, full-page `/search` may re-rank **properties** with keyword + stored `PropertyEmbedding` cosine scores (weighted merge). Autocomplete stays keyword-only. Rule-based constraints (beds, price, type) apply as hard filters when confidence is high. If embeddings missing/provider fails → keyword path + `hybrid.degraded`. Never logs raw query. See `docs/CRM_INTELLIGENCE_CONTRACT.md`.

## Customer NL filters (optional)
`ENABLE_CUSTOMER_NL_FILTERS` / admin key `customer_nl_filters` — default `0`. When on, customer scope applies high-confidence structured filters on `budget_*`, `preferred_bedrooms`, `preferred_type`, `location_preference`. Response may include `customer_nl.hard_filters` / `chips`. Free-text `preferences` is never searched. Flag off = classic name/email/phone/location keyword only.

## Activity search (optional)
`ENABLE_ACTIVITY_SEARCH` / admin key `activity_search` — default `0`. When on, `scope=activities` searches **only** `interaction_type`, `outcome`, and numeric id. **Never** `body` or `subject`. Soft-deleted interactions and customers excluded. Hits link to Customer 360.


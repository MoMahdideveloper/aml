# Vocabulary contract (Track A, PR1)

## Purpose
Staff-managed lexicon for **query-side** expansion of property keyword search.
Does **not** rewrite stored listing text. Does **not** auto-create synonyms from embeddings.

## Layers

| Layer | Direction | Mutates DB text? | Auto from embeddings? |
|-------|-----------|------------------|------------------------|
| Normalize | text → key | No | N/A |
| Synonym | bidirectional expand (default) | No | **No** |
| Replacement | directional from → to on query tokens | No | No |
| Occurrence | entity field index (v2) | No | No |

## Normalize rules
1. Unicode NFKC  
2. Strip / collapse whitespace  
3. Casefold  
4. Strip edge punctuation  

## Expand algorithm
1. Tokenize query on whitespace; also treat full query as a token.  
2. Normalize each token.  
3. Apply active **replacement** (highest priority wins per `from_key`).  
4. Expand via active **synonym** groups (bidirectional membership).  
5. Cap at **8** keys total (including original query string when used for search).  

## Search integration
- Flag: `ENABLE_VOCAB_ENRICHMENT` (default `0`).  
- When on: property scope (`title`, `address`, `neighborhood`, `file_code`, id).  
- When off: identical to pre-vocab keyword search.  
- **Customer expand (optional):** when `ENABLE_CUSTOMER_NL_FILTERS=1` **and** vocab enrichment on, expand may also match `location_preference` / `preferred_type` (never free-text `preferences`).  
- Deals / agents / tasks: **no** expand.  
- Description body: only if `ENABLE_DESCRIPTION_SEARCH=1`.  

## Admin
- `/admin/vocab` — create/archive terms, synonyms, replacements.  
- Soft archive only.  
- Admin CRUD available regardless of expand flag.  

## Telemetry
Log `vocab_expanded`, `expanded_term_count`, duration, hit counts.  
**Never** log raw query text or synonym free-text payloads beyond staff lexicon ids.

## Occurrences (v2)
- Flag: `ENABLE_VOCAB_OCCURRENCES` (default `0`).
- Table `vocab_occurrences`: entity_type, entity_id, field, normalized_key, term_id, source_hash, confidence, status.
- Extract from allowlisted fields only; never rewrites description text.
- Celery: `crm.reindex_vocab_occurrences`.

## Non-goals
Neo4j, embedding-mined synonyms, auto-synonym from similarity.

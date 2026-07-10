# CRM intelligence (Track A) — contract overview

Incremental capabilities on the Flask CRM only (ADR-001 Track A). Track B / Neo4j are **not** required.

## Capability map

| Capability | Status | Flag |
|------------|--------|------|
| Vocabulary (normalize / synonym / replacement) | **PR1 shipped** | `ENABLE_VOCAB_ENRICHMENT` (expand; default `0`) |
| Hybrid / NL semantic property search | Planned PR2 | `ENABLE_HYBRID_SEARCH` |
| AI context packets | Planned PR3 | `ENABLE_AI_CONTEXT` |
| Derived relationship edges (SQL) | Planned PR4 | `ENABLE_DERIVED_EDGES` |
| LLM query parse | Optional later | `ENABLE_NL_QUERY_PARSE` |

## Privacy
- Never log raw search queries, description bodies, or interaction note bodies.  
- Context packets (future) use allowlisted fields + provenance + char budgets.  

## Failure modes
- Vocab/lexicon errors → fall back to unexpanded keyword search.  
- Future embedding provider down → keyword-only + `degraded` meta.  

## Related docs
- `docs/VOCAB_CONTRACT.md`  
- `docs/SEARCH_CONTRACT.md`  
- `docs/SEARCH_FIELD_ALLOWLIST.md`  

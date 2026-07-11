# CRM intelligence (Track A) — contract overview

Incremental capabilities on the Flask CRM only (ADR-001 Track A). Track B / Neo4j are **not** required.

## Capability map

| Capability | Status | Flag |
|------------|--------|------|
| Vocabulary (normalize / synonym / replacement) | **PR1 shipped** | `ENABLE_VOCAB_ENRICHMENT` (expand; default `0`) |
| Hybrid / NL semantic property search | **PR2 shipped** | `ENABLE_HYBRID_SEARCH` (default `0`) |
| AI context packets | **PR3 shipped** | `ENABLE_AI_CONTEXT` (default `0`) |
| Derived relationship edges (SQL) | **PR4 shipped** | `ENABLE_DERIVED_EDGES` (default `0`) |
| Operator guide / rollout polish | **PR5** | (docs; flags remain default `0`) |
| Intelligence v2 (occurrences, evidence, task/agent, edges) | **shipped** | `ENABLE_VOCAB_OCCURRENCES` + existing |
| Admin intelligence settings UI | **shipped** | `/admin/intelligence` (DB toggles) |
| SearchIntent + context matches/briefs + match edges | **shipped** | extends hybrid/context/graph |
| Grounded AI answers | **shipped** | `ENABLE_AI_ANSWER` / admin toggle |
| LLM query parse | Optional later | `ENABLE_NL_QUERY_PARSE` |
| Customer NL structured filters | **Shipped** | `ENABLE_CUSTOMER_NL_FILTERS` / admin `customer_nl_filters` (default `0`) |
| Embedding coverage metric | **Shipped** | `/admin/intelligence` panel (counts only) |
| Customer completeness section | **Shipped** | Included in AI context when context on |


## Privacy
- Never log raw search queries, description bodies, or interaction note bodies.  
- Context packets use allowlisted fields + provenance + char budgets.  

## Failure modes
- Vocab/lexicon errors → fall back to unexpanded keyword search.  
- Embedding provider down / no vectors → keyword-only + `hybrid.degraded` meta.  
- Context / edges flags off → HTTP 404 on their APIs.  

## Related docs
- `docs/CRM_INTELLIGENCE_OPERATOR.md` — rollout, flags, rollback  
- `docs/VOCAB_CONTRACT.md`  
- `docs/SEARCH_CONTRACT.md`  
- `docs/AI_CONTEXT_CONTRACT.md`  
- `docs/RELATIONSHIP_EDGES_CONTRACT.md`  
- `docs/SEARCH_FIELD_ALLOWLIST.md`  



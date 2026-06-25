# PB4 Manual Summary

- stage: `PB4`
- captured_at: `2026-02-18T18:06:31.7862870-06:00`
- source_chat: `https://gemini.google.com/app/9d959ffe030d5031`

## Response Highlights
- Defined failure decision tree for:
  - Gemini outage
  - vector outage
  - combined outage
  - stale embeddings
  - background worker timeouts
- Proposed unified fallback contract with `matches[]` and `meta` flags (`is_fallback`, `is_degraded`, `match_method`, `degradation_reason`) to preserve response compatibility.
- Recommended deterministic degraded ranking strategy with explicit multi-level sort keys and strict tie-breakers.
- Defined UI degradation behavior:
  - downgrade badges/score display for SQL fallback
  - disable copilot actions during AI fallback
  - avoid disruptive error toasts for expected degraded states
- Added observability baseline: structured events, metrics, and alert thresholds.
- Returned 12 reliability tests spanning service, worker, deterministic ordering, and frontend fallback behavior.

## Decisions For This Repo
1. Standardize fallback metadata across recommendation APIs and worker outputs.
2. Keep deterministic ordering in all fallback modes to avoid pagination instability.
3. Expose degraded state explicitly to frontend for controlled UI behavior.
4. Add health metrics and alerting for fallback rates and worker timeout frequency.

# PB3 Manual Summary

- stage: `PB3`
- captured_at: `2026-02-18T18:04:14.2670298-06:00`
- source_chat: `https://gemini.google.com/app/9d959ffe030d5031`

## Response Highlights
- Produced threat-to-fix matrix covering:
  - API auth redirect leakage (`302` vs JSON `401`)
  - IDOR on pitch/match resources
  - CSRF bypass on mutating AI trigger endpoints
  - prompt-injection handling with strict schema/fallback
- Proposed endpoint policy matrix for new routes with explicit auth/CSRF and no redirect for API paths.
- Recommended session cookie hardening profile for production-safe defaults.
- Defined frontend handling contract for `401/403/404/5xx` to avoid broken modal/UI flows.
- Returned a concrete 12-test security regression suite including auth shape, CSRF, IDOR, sanitization, DoS/rate limit, and fallback behavior.

## Decisions For This Repo
1. Preserve strict JSON unauthorized behavior for all `/api/*` and XHR calls.
2. Enforce ownership scoping on new matchmaker/copilot resources to prevent IDOR.
3. Keep CSRF enabled for mutating AI endpoints and wire token usage in existing request wrappers.
4. Treat AI/provider failures as deterministic fallback responses, not hard server errors.

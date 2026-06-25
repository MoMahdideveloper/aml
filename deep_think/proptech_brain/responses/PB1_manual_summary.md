# PB1 Manual Summary

- stage: `PB1`
- captured_at: `2026-02-18T17:59:15.8913850-06:00`
- source_chat: `https://gemini.google.com/app/9d959ffe030d5031`

## Response Highlights
- Proposed dependency order: schema -> LLM/provider -> search/vector scoring -> async jobs -> views/API -> frontend.
- Suggested schema extension to support dual scores and Smart Context fields plus weekly trend storage.
- Recommended new Gemini service/provider methods with strict JSON and deterministic fallback behavior.
- Kept heavy work async via Celery tasks and weekly beat schedule.
- Added read-only JSON endpoints for pitch and trend delivery, then UI enhancements for badges and copilot CTA.
- Listed auth/CSRF safety boundaries to keep untouched in early rollout.
- Returned 10 acceptance tests spanning unauthorized JSON behavior, CSRF enforcement, fallback paths, async queuing, and UI rendering.

## Decisions For This Repo
1. Keep auth/CSRF/error envelope in `app.py` unchanged; implement features in additive layers only.
2. Implement async-first enrichment/scoring/pitch generation; no request-path LLM calls.
3. Preserve recommendation route contracts and extend with explicit versioned/new endpoints where needed.
4. Translate PB1 into concrete implementation tasks across model, services, celery, views, and frontend files.

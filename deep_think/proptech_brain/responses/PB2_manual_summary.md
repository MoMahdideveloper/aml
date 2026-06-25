# PB2 Manual Summary

- stage: `PB2`
- captured_at: `2026-02-18T18:01:50.4211793-06:00`
- source_chat: `https://gemini.google.com/app/9d959ffe030d5031`

## Response Highlights
- Defined strict JSON contract for Smart Context output:
  - `smart_benefits[]`
  - `trending_badges[]`
  - `confidence_score`
  - `is_fallback`
  - `metadata`
- Recommended enforcing JSON-only generation using `response_mime_type="application/json"` plus `response_schema` in Gemini provider.
- Suggested additive storage strategy: one `smart_context` JSON field on `Property` for 1:1 listing enrichment.
- Trigger model: enqueue async enrichment task after successful listing create/update/image commit; never block request path.
- Failure contract: deterministic fallback payload persisted when Gemini call fails or retries exhaust.
- Proposed Celery retry policy with bounded retries and exponential backoff for transient provider errors.
- Added test matrix for schema parsing, fallback behavior, task transaction safety, and UI async rendering.

## Decisions For This Repo
1. Implement `analyze_multimodal_context()` as strict JSON return contract with mandatory fallback marker.
2. Keep enrichment pipeline asynchronous through Celery tasks only.
3. Persist Smart Context in property-scoped JSON storage first, then consider indexes only when filter/search needs emerge.
4. Add UI loading/fallback states for incomplete enrichment, not hard failures.

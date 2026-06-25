# P4 Deep Think Response (Captured Summary)

## 1) Decision Tree Contract

- Request first passes `app.py` auth middleware for request-type split:
- API/XHR unauthenticated -> JSON `401` (no redirect).
- Browser HTML unauthenticated -> `302` to login with safe `next`.
- Normal recommendations path:
- `views/main.py` -> `services/gemini_service.py` -> `services/llm/providers/gemini_provider.py`.
- On valid AI response -> enrich/rank -> `200`.
- Degraded AI paths:
- Provider timeout or provider error -> catch in `gemini_service.py` -> delegate fallback search -> `is_fallback=True`.
- Malformed model output -> parsing/validation failure -> same fallback path.
- Vector failure path:
- `services/vector_service.py` failure handled in `services/search_service.py` -> degrade to keyword-only ranking -> no user-facing `500` for handled degradation.

## 2) Deterministic Fallback Ranking

- Primary fallback score:
- `total_score = semantic_score * 0.70 + keyword_score * 0.30`
- If vector is unavailable:
- `total_score = keyword_score * 1.0`
- Stable tie-break order:
- `total_score DESC` -> `property_rating DESC` -> `nightly_price ASC` -> `property_id ASC`.

## 3) UX/Error Contract

- API/XHR:
- `401` JSON unauthenticated.
- `200` JSON for AI success and for fallback success (`meta.is_fallback` + reason).
- `500` JSON only for unrecoverable system failures.
- Browser HTML:
- `302` to login when unauthenticated.
- `200` recommendations page for both AI and fallback paths.
- Fallback should show explicit banner message indicating degraded AI mode.

## 4) Regression and Acceptance Focus

- Must eliminate redirect loops for API/XHR fallback paths (TC007/TC013).
- Must guarantee fallback on provider timeout and malformed output.
- Must guarantee deterministic ordering for identical fallback inputs.
- Must verify vector outage degradation path stays functional.

## 5) Priority Backlog Lines

- P0 regression: Enforce strict API-vs-browser auth contract in `app.py` middleware (`401/403` JSON for API/XHR, `302` for browser flows) with integration tests for TC007/TC013.
- P0 regression: Implement deterministic fallback ranking and vector-failure degradation in `services/search_service.py` and `services/vector_service.py`.
- P1 regression: Harden provider timeout/error and malformed-output handling in `services/llm/providers/gemini_provider.py` and `services/gemini_service.py`.
- P1 regression: Refactor `views/main.py` recommendations/export handlers to propagate `is_fallback` metadata and consistent UX messaging for degraded mode.

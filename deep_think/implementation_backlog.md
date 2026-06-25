# Implementation Backlog (Derived from Deep Think Responses)

- generated_at: `2026-02-18T22:06:20Z`
- sources: `5`
- parsed_items: `14`

| Priority | Stage | Risk | Summary | Change Scope | Tests Needed |
|---|---|---|---|---|---|
| P0 | P2 | security | - P0 security: Inject CSRF token source in `templates/base.html` and enforce token/header propagation in `static/js/crud-utils.js`. | templates/base.html, static/js/crud-utils.js | integration |
| P1 | P2 | security | - P1 regression: Return deterministic JSON CSRF/auth error contracts for AJAX in `app.py` to avoid frontend parser crashes. | app.py | integration |
| P1 | P2 | regression | - P1 regression: Refactor modal/action event binding in `static/js/main.js` and related view payload wiring in `views/properties.py` for dynamic DOM stability. | static/js/main.js, views/properties.py | integration |
| P0 | P3 | security | - P0 security: Enforce API/XHR auth contract and RBAC in `app.py` (`401/403` JSON, `/admin/*` role gate), with integration tests for TC007/TC012. | app.py | integration |
| P0 | P3 | security | - P0 security: Implement CSRF token propagation contract across `templates/base.html` and `static/js/crud-utils.js`; remove broad exemptions; validate TC010. | templates/base.html, static/js/crud-utils.js | integration |
| P1 | P3 | security | - P1 security: Enforce login/session cookie hardening in `app.py` and verify `Set-Cookie` flags with auth regression tests. | app.py | integration |
| P0 | P4 | security | - P0 regression: Enforce strict API-vs-browser auth contract in `app.py` middleware (`401/403` JSON for API/XHR, `302` for browser flows) with integration tests for TC007/TC013. | app.py | integration |
| P0 | P4 | regression | - P0 regression: Implement deterministic fallback ranking and vector-failure degradation in `services/search_service.py` and `services/vector_service.py`. | services/search_service.py, services/vector_service.py | integration |
| P1 | P4 | regression | - P1 regression: Harden provider timeout/error and malformed-output handling in `services/llm/providers/gemini_provider.py` and `services/gemini_service.py`. | services/llm/providers/gemini_provider.py, services/gemini_service.py | integration |
| P1 | P4 | data | - P1 regression: Refactor `views/main.py` recommendations/export handlers to propagate `is_fallback` metadata and consistent UX messaging for degraded mode. | views/main.py | integration |
| P0 | P5 | security | - P0 security: Implement strict unauthorized response split in `app.py` and eliminate blanket CSRF exemptions; ensure `templates/base.html` + `static/js/crud-utils.js` provide working CSRF token propagation. | app.py, templates/base.html, static/js/crud-utils.js | integration |
| P0 | P5 | regression | - P0 regression: Eliminate baseline frontend runtime breakage in `static/js/main.js` and `static/js/crud-utils.js` so critical CRUD/UI flows initialize reliably. | static/js/main.js, static/js/crud-utils.js | integration |
| P1 | P5 | data | - P1 regression: Stabilize modal routing and teardown behavior in `views/properties.py`, `views/main.py`, and `static/js/main.js` without changing public API schema. | views/properties.py, views/main.py, static/js/main.js | integration |
| P2 | P5 | regression | - P2 regression: Implement deterministic degraded recommendation orchestration in `services/search_service.py`, `services/vector_service.py`, `services/gemini_service.py`, and `services/llm/providers/gemini_provider.py`. | services/search_service.py, services/vector_service.py, services/gemini_service.py, services/llm/providers/gemini_provider.py | integration |

## Acceptance Checks
- Every high-severity failure should map to at least one backlog item.
- Wave ordering should remain dependency-ordered.
- Each P0/P1 item should include at least one regression test.

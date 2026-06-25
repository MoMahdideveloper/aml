# P3 Deep Think Response (Captured Summary)

## 1) Threat-to-Fix Matrix (Condensed)

- TC010 (CSRF/session): add CSRF meta source + AJAX `X-CSRFToken` injection, enforce secure session cookie flags.
- TC012 (admin auth): enforce explicit RBAC (`session["role"] == "admin"`) on `/admin/*` and `/api/admin/*`.
- TC007 (fallback confusion): return JSON `401/403` for API/XHR; keep browser route redirects for HTML paths; validate `next` to prevent open redirects.

## 2) Middleware Policy Contract

- API/XHR unauthenticated requests: return JSON `401`, no redirect.
- API/XHR unauthorized role: return JSON `403`.
- Browser HTML routes unauthenticated: redirect `302` to `/login?next=...` with safe relative-path validation.
- Admin HTML routes: unauthenticated -> `302`; authenticated non-admin -> `403` template.

## 3) CSRF Hardening Sequence

1. Keep global `CSRFProtect(app)` enabled in `app.py`; remove broad `@csrf.exempt` on core CRUD/export/auth paths.
2. Inject `<meta name="csrf-token" content="{{ csrf_token() }}">` in `templates/base.html`.
3. Patch `static/js/crud-utils.js` to attach `X-CSRFToken` and `X-Requested-With` for `POST/PUT/PATCH/DELETE`.
4. Handle CSRF expiry UX deterministically in frontend (`400` contract -> refresh/session-expired message).

## 4) Regression Test Targets

- Auth/RBAC: `/admin/*` and `/api/admin/*` role tests (`403` HTML vs `403` JSON).
- Fallback behavior: API unauthenticated must return `401` JSON, not `302` HTML.
- CSRF path: mutation requests with/without token (`400` vs success).
- Session cookie flags on login response (`HttpOnly`, `Secure`, `SameSite=Lax`).

## 5) Safe Rollout and Feature Flags

- `FLAG_AJAX_CSRF_ENFORCEMENT`: phase-in strict CSRF header enforcement for AJAX mutations.
- `FLAG_STRICT_RBAC_FALLBACK`: phase-in strict auth response segregation and admin RBAC checks.
- Rollback triggers: CSRF `400` spike on CRUD APIs, or verified admin/user flow regressions after strict auth enablement.

## 6) Priority Backlog Lines

- P0 security: Enforce API/XHR auth contract and RBAC in `app.py` (`401/403` JSON, `/admin/*` role gate), with integration tests for TC007/TC012.
- P0 security: Implement CSRF token propagation contract across `templates/base.html` and `static/js/crud-utils.js`; remove broad exemptions; validate TC010.
- P1 regression: Add deterministic CSRF/auth error response handling for AJAX consumers and explicit browser-vs-API fallback tests.
- P1 security: Enforce login/session cookie hardening in `app.py` and verify `Set-Cookie` flags with auth regression tests.

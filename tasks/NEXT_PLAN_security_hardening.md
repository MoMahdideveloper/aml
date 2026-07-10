# Next Full Plan: Track A Security Hardening

**Give this plan to another agent after:**

1. Release-readiness / deprecation / a11y-perf work is finished or isolated in another worktree  
2. **Data integrity / backup / DR** plan (`tasks/NEXT_PLAN_data_integrity_backup_dr.md`) at least has an approved recovery contract (`docs/BACKUP_RECOVERY_CONTRACT.md`) — security can run in parallel with DR **if** they do not both edit CI/`docs/PRODUCTION.md` without coordination  

**This scope is independent** of UI redesign, accessibility polish, performance asset work, and Pydantic/datetime deprecation.

---

## Mission

Prove and harden **server-side security** for Track A Platinum Heritage Flask CRM: authentication, session cookies, authorization/IDOR, CSRF, input validation, XSS, sensitive data leakage, admin environment controls, LLM/outbound boundaries, security headers, supply-chain hygiene, audit logging, and CI gates.

Preserve product behavior for legitimate authorized users. Prefer **tests that expose gaps first**, then smallest fixes. Do not invent multi-tenancy the product does not have — document actual access model from code.

---

## Hard Boundaries

- **Track A only.** Do not modify `api/`, `matcher/`, `ingestor/`, `chatbot/`, or Neo4j matching stack.
- Never touch dirty generated paths: `chroma_db/`, `graphify-out/`, `node_modules/`, `server.pid`, Stitch exports.
- Synthetic data only. No production credentials, no real customer dumps.
- Do not commit, push, delete archives, or alter production systems without explicit approval.
- Do not print secret values when scanning for leaks — report **path + pattern type** only.
- Coordinate with release/DR agents before changing migrations, core CI, or `docs/PRODUCTION.md`.
- No broad auth framework rewrite unless tests prove route-level enforcement is systematically broken.
- Rate-limit **policy** changes require human approval (report recommendations first).

---

## Context (repo anchors)

| Area | Current anchors |
|------|-----------------|
| App factory / cookies / CSRF / CSP | `app.py` |
| Auth routes | `views/auth.py`, `templates/auth_*.html` |
| Admin env | `views/admin_environment.py`, `tests/test_environment_*.py` |
| Prod config tests | `tests/test_production_config.py`, `tests/test_auth_cookie_hardening.py` |
| Health | `/healthz`, `/readyz` |
| Forms | `forms.py`, modal POST routes |

---

## Architecture Decisions

1. **Security is server-enforced.** Hidden buttons and client JS are not controls.
2. **Discover routes from Flask URL map**, not manual guessing.
3. **Document actual role model from code** (global CRM vs true ownership) before inventing tenants.
4. **Deny-first tests** for anonymous / ordinary / privileged identities.
5. **CSRF** required for browser session mutations when CSRF enabled; tests must not globally disable CSRF except isolated fixtures.
6. **LLM/tool output is untrusted** — parse/validate; never execute as SQL/shell/path/HTML.
7. **Logs redacted** — useful security events, never passwords/tokens/secrets/full PII payloads.

---

## Dependency Graph

```text
Threat model + role model from code
    │
    v
Route authorization matrix (Flask URL map)
    │
    v
Auth lifecycle + session cookie production behavior
    │
    v
IDOR / deny-first domain tests
    │
    v
CSRF + input validation + XSS
    │
    v
Sensitive serialization + admin env + LLM boundaries
    │
    v
Headers + dependency/secret scan
    │
    v
Security event logging + CI security suite
```

---

## Phase 1: Threat Model and Route Matrix

### Task 1: Confirm product access model

**Description:** Read auth, admin, and CRUD views. Document who can access what **as implemented today**.

**Acceptance criteria:**
- [x] Roles/identities listed (anonymous, authenticated user, admin if any).
- [x] Whether data is global to all logged-in users or scoped by agent/owner — explicit statement.
- [x] High-value assets: customers, properties, deals, media, env secrets, AI keys.

**Likely files:** `views/auth.py`, `views/admin_environment.py`, `views/**/*.py`, existing auth tests.

**Estimated scope:** S.

**Status:** Documented in `docs/SECURITY_ROUTE_MATRIX.md` + Phase 3 authz artifact (global staff CRM).

### Task 2: Build authorization route matrix

**Description:** Enumerate every Track A endpoint from `app.url_map`.

For each route record: method, endpoint name, auth expectation, CSRF relevance, sensitivity.

**Acceptance criteria:**
- [x] Every Track A endpoint appears once.
- [x] Missing/inconsistent checks are explicit findings ranked critical/high/medium/low.
- [x] Matrix stored as `docs/SECURITY_ROUTE_MATRIX.md` or `artifacts/security_route_matrix.md` (synthetic only).

**Likely files:** `app.py`, `views/*.py`, blueprint modules, forms, API-ish JSON routes under Track A.

**Estimated scope:** M.

---

## Checkpoint 1

- [x] Threat model seed notes in `docs/SECURITY_ROUTE_MATRIX.md`.
- [x] Route matrix complete (auto-exported; **140** non-static endpoints).
- [x] Findings ranked (F1–F4 seed table in matrix doc).
- [x] Access model treated as **global staff CRM** from code (ownership not invented). Re-open if product changes.
- [x] AuthZ tests match global model; no multi-tenancy invented.

**Note:** `AUTH_DEFAULT_DENY_ENABLED` middleware is implemented (default on).

Regenerate matrix:

```powershell
python scripts/export_security_route_matrix.py --out docs/SECURITY_ROUTE_MATRIX.md
```

---

## Phase 2: Authentication and Session Security

### Task 3: Test authentication lifecycle

Cover:

- Valid/invalid login
- Logout invalidates session
- Session fixation resistance
- Safe redirect after login (no open redirect)
- Disabled/deleted user behavior
- Generic errors (limit account enumeration)

**Acceptance criteria:** Protected routes reject anonymous users; external `next` URLs cannot open-redirect; identity change does not reuse attacker-controlled pre-login session unsafely.

**Likely files:** `views/auth.py`, `tests/test_auth_*.py` (extend).

**Estimated scope:** M.

**Status (2026-07-10):** Done.
- Implemented `register_auth_middleware` in `app.py` (`AUTH_DEFAULT_DENY_ENABLED`, default `1`).
- Session fixation: `session.clear()` + `session.permanent` on successful login; full clear on logout.
- Safe relative `next_url` from deny middleware; open redirects rejected by `_is_safe_next_url`.
- Tests: `tests/test_auth_default_deny.py`, `tests/test_auth_lifecycle.py`, `tests/test_auth_cookie_hardening.py`.
- Suite opt-out: `tests/conftest.py` sets `AUTH_DEFAULT_DENY_ENABLED=0` for legacy open-route tests.

### Task 4: Harden production session configuration

Verify:

- `SESSION_COOKIE_HTTPONLY=True`
- `SESSION_COOKIE_SECURE=True` under HTTPS production
- `SESSION_COOKIE_SAMESITE=Lax` (or stricter with justification)
- Finite session lifetime
- Secret required / fail-closed in production
- Trusted proxy HTTPS only for known topology

**Acceptance criteria:** Production cookie tests pass; dev remains usable; no default secret accepted in production.

**Likely files:** `app.py`, `tests/test_production_config.py`, `tests/test_auth_cookie_hardening.py`.

**Estimated scope:** S.

**Status (2026-07-10):** Verified existing contract (no code change required).
- HttpOnly / SameSite=Lax / Secure-in-prod / finite lifetime / fail-closed secret covered by `test_production_config.py` + `test_auth_cookie_hardening.py`.
- Trusted-proxy HTTPS topology still deferred (ops/deploy config).

### Task 5: Verify login abuse controls

Inspect rate limiting / lockout. Test repeated failures, window, untrusted `X-Forwarded-*`, recovery after success.

**Policy changes require human approval** — report recommended values first.

**Acceptance criteria:** Automated guessing gets controlled response; limiter not bypassable via untrusted forwarding headers.

**Likely files:** rate-limit config, `views/auth.py`, limiter extensions.

**Estimated scope:** S–M.

**Status (2026-07-10 / completed):** Login rate limit wired.
- `ENABLE_LOGIN_RATE_LIMIT=1` or production → `10 per 15 minutes` (override `LOGIN_RATE_LIMIT`).
- Dev/test exempt unless flag set; storage default `memory://` (`RATELIMIT_STORAGE_URI`).
- Tests: `tests/test_security_events.py::test_login_rate_limit_when_enabled`.

---

## Phase 3: Authorization and Object Isolation

### Task 6: Deny-first authorization tests

For each CRUD domain (properties, customers, agents, deals, tasks, recommendations, media), use at least:

- anonymous
- ordinary authenticated
- privileged/admin **if product supports it**

Test read/create/update/delete via **direct URL/API**, not only UI.

**Acceptance criteria:** 401/403 for unauthorized; protected data never in denial body.

**Estimated scope:** L (split by domain if needed).

**Status (2026-07-10):** Done via `tests/test_authz_deny_first.py` (14 tests).
- Anonymous HTML/API/mutations denied with no sensitive body leakage.
- Authenticated staff can read global CRM; `viewer` role same as agent today (F6).
- Admin environment requires `admin_authenticated`, not mere `user_id`.

### Task 7: IDOR / BOLA resistance

Attempt ID tampering for properties, customers, agents, deals, tasks, recommendations, media.

**Do not invent multi-tenancy.** If product is global-for-auth-users, document that as intentional and still test admin-only surfaces.

**Acceptance criteria:** Cross-scope access impossible under actual rules; unnecessary sensitive distinctions not leaked.

**Estimated scope:** M–L.

**Status (2026-07-10):** Documented + contract-tested as **global staff CRM**.
- Cross-agent customer/deal/task ID access is **allowed by design** (tests encode this).
- Admin surfaces remain isolated from ordinary CRM session.
- Access model written in `docs/SECURITY_ROUTE_MATRIX.md` and `artifacts/SECURITY_PHASE3_AUTHZ.md`.
- No ownership middleware invented.

### Task 8: Centralize repeated permission checks

Only after tests expose duplication/inconsistency: smallest decorator/helper. Keep ownership checks near service/repository when routes can be bypassed.

**Acceptance criteria:** One canonical policy per repeated rule; authorized behavior unchanged.

**Estimated scope:** S–M.

**Status (2026-07-10):** No new decorator required.
- Authentication already centralized in `register_auth_middleware` (`app.py`).
- Admin already uses `require_admin_auth` on env routes.
- Object ownership is not a product rule → no ownership helper without a product change.
- If role scopes (`viewer` read-only) are desired later, add one helper after F6 is accepted as a change request.

---

## Checkpoint 2

- [x] Anonymous and cross-user access tests pass under real model (`test_authz_deny_first.py`).
- [x] Destructive/mutating endpoints require auth under default-deny (anon → login/401); shared mutability among staff is intentional.
- [x] UI visibility not treated as security control (tests hit URLs/APIs directly).
- [x] Login rate limits implemented (env/production gated).
- [ ] **Still optional product decisions:** (1) enforce `viewer` read-only, (2) per-agent ownership.

---

## Phase 4: Request Integrity and Input Validation

### Task 9: CSRF coverage

State-changing browser ops: create/update/delete forms, modals, AJAX, task complete, recommendation dismiss, admin env changes.

Use POST/PUT/PATCH/DELETE; reject mutation via GET.

**Acceptance criteria:** Missing/invalid CSRF fails for session browser mutations when CSRF on; reads unaffected.

**Estimated scope:** M.

**Status (2026-07-10):** Done.
- Server: `tests/test_security_csrf.py` (ENABLE_CSRF=1) — missing/invalid token does not mutate; field + `X-CSRFToken` header succeed; GET reads OK.
- Frontend contract: agents fetch, property_details AI helper, `main.js` AI autofill send CSRF (`tests/test_csrf_frontend_contract.py`).
- HTML CSRF failures map to 400 handler → redirect dashboard (no mutation).

### Task 10: Boundary input validation

Missing fields, excessive lengths, invalid enums, malformed IDs/dates, negative numbers, unknown fields, duplicate submits, content-type mismatch.

**Acceptance criteria:** Controlled 400/422; DB unchanged; no stack traces to client.

**Estimated scope:** M.

**Status (2026-07-10):** Done via `tests/test_security_input_validation.py`.
- WTForms rejects invalid email, long name, negative budget, missing FKs; DB unchanged.
- Malformed path IDs → 404/400/302 without stack traces.
- Unknown query params on list pages do not 500.

### Task 11: XSS and unsafe rendering

Search `|safe`, `Markup`, `innerHTML`, raw HTML, unescaped JSON. Test stored payloads in names, descriptions, tasks, flashes, LLM content.

**Acceptance criteria:** User/model content text-safe unless intentionally sanitized; no script execution.

**Estimated scope:** M.

**Status (2026-07-10):** Done via `tests/test_security_xss.py`.
- Stored `<script>` payloads escaped on customers/agents/tasks/properties HTML.
- JSON APIs return raw strings with `application/json` (not HTML).
- `|safe` inventory locked to intentional uses: `properties_json`, modal `content`/`footer`.

---

## Phase 5: Sensitive Data and External Boundaries

### Task 12: Response serialization audit

JSON, templates, logs, error handlers: no password hashes, API keys, session IDs, filesystem paths, full traces, unnecessary PII.

**Acceptance criteria:** Allowlists for sensitive entities; generic production errors.

**Estimated scope:** M.

**Status (2026-07-10):** Done via `tests/test_security_sensitive_data.py`.
- `User.to_dict()` excludes `password_hash`; CRM JSON APIs do not emit hashes/session secrets.
- JSON 500 handler returns generic message (no traceback/paths).
- `/healthz` / `/readyz` free of secrets.

### Task 13: Secure admin environment operations

View/create/update/delete/validate/health for environment keys.

Controls: admin permission, redaction, no secret after write, audit without value, protected keys policy.

**Acceptance criteria:** Ordinary users cannot discover secrets; logs never contain values; failed changes roll back.

**Likely files:** `views/admin_environment.py`, `tests/test_environment_*.py`.

**Estimated scope:** M.

**Status (2026-07-10):** Done + small leak hardening.
- Sensitive keys masked on list/details/history; CRM user cannot open admin env.
- Create returns masked value; dup create raises and rolls back.
- Admin error responses/flashes no longer echo raw `str(e)` for unexpected/runtime paths.
- Protected keys (`*_API_KEY`, SESSION_SECRET, …) already blocked from DB management.

### Task 14: Constrain LLM and outbound integrations

Untrusted prompts/output. Timeouts, retries, no SSRF via user URLs, token limits, no secrets in prompts.

**Acceptance criteria:** Structured output validated; tests use fakes only.

**Estimated scope:** M.

**Status (2026-07-10):** Documented + tested with fakes.
- Extract endpoints use fakes; provider failures return generic JSON errors.
- Gemini/KIE providers expose positive timeouts (≤120s).
- Nominatim geocode only hits fixed host; free-text is query param (no user-controlled URL SSRF).
- LLM JSON fields treated as data (script strings not executed server-side).

---

## Phase 6: Security Headers and Supply Chain

### Task 15: Response security headers

CSP, HSTS (HTTPS prod), `X-Content-Type-Options`, frame protection, `Referrer-Policy`, `Permissions-Policy`, cache controls for sensitive pages.

**Acceptance criteria:** Header tests at response level; CSP matches Leaflet/fonts/static reality without reckless wildcards.

**Likely files:** `app.py`, production tests.

**Estimated scope:** S.

**Status (2026-07-10):** Done.
- Tests: `tests/test_security_headers.py`.
- `/auth/*` and `/admin/*` get `Cache-Control: no-store…`.
- Production CSP + HSTS covered; CSP opt-in via `ENABLE_CSP=1` in dev.

### Task 16: Dependencies and secrets scan

Python/JS audits; fix or document critical/high with owner + date. Scan tracked files for credential patterns **without printing values**.

**Acceptance criteria:** Lockfiles reproducible; real secret → rotation recommendation only.

**Estimated scope:** S–M.

**Status (2026-07-10):** Done (scan + lockfile inventory).
- `scripts/scan_secrets.py` — path/line/pattern only; CI step writes `artifacts/SECRET_SCAN.json`.
- Latest: **0 high**; 1 medium (`n8n_data.md` bearer-like); lows = default-password docs/tests.
- Lockfiles: `requirements.txt`, `uv.lock`, `package-lock.json` present.
- `pip-audit` / `npm audit` optional (not wired as blocking CI yet).

See `artifacts/SECURITY_PHASE6_HEADERS_SUPPLY.md`.

---

## Phase 7: Auditability and Regression Gates

### Task 17: Security event logging

Log: login success/failure, logout, permission denial, destructive actions, admin config changes, repeated validation failures.

Structured fields + correlation ID. Never log passwords/tokens/cookies/secrets/full sensitive payloads.

**Acceptance criteria:** Tests assert event presence and redaction.

**Estimated scope:** M.

**Status (2026-07-10):** Done.
- `utils/security_events.py` + redaction + automatic `request_id`.
- Events: login success/failure, logout, auth_denial, destructive deletes, admin_config_change (no values).
- Correlation: `g.request_id` / `X-Request-ID` request+response headers.
- Tests: `tests/test_security_events.py`.

### Task 18: Focused CI security suite

Fast tests: anonymous denial, role denial, object isolation, CSRF rejection, open redirect rejection, secure cookies/headers, secret redaction, generic production errors.

Keep network-heavy dependency audit separate if flaky.

**Acceptance criteria:** Security regressions fail CI deterministically; synthetic data; practical runtime.

**Likely files:** `tests/test_security_*.py`, `.github/workflows/tests.yml` (coordinate with release/DR).

**Estimated scope:** M.

**Status (2026-07-10):** Done for Track A core CI.
- Core job includes auth lifecycle, authz, CSRF, validation, XSS, sensitive data, headers, secret-scan unit tests, security events + `scan_secrets.py` gate.

---

## Final Verification

```powershell
python -m pytest -q tests/test_security*.py tests/test_production_config.py --tb=short
python -m pytest -q tests/test_environment_views.py tests/test_environment_service.py --tb=short
python -m pytest -q tests/test_app_smoke.py tests/test_platinum_heritage_ui.py tests/test_template_replacement.py --tb=short
```

Browser (synthetic users): anonymous, ordinary, privileged — cookies, headers, network, denial bodies.

---

## Definition of Done

- [x] Every Track A route in authorization matrix.
- [x] AuthN/AuthZ server-enforced (default-deny + admin isolation; global staff data model documented).
- [x] IDOR tests match real product model (global CRM contract tests).
- [x] Browser mutations have method + CSRF control.
- [x] Inputs bounded before persistence (WTForms + validation tests).
- [x] No user/model content executes as HTML/SQL/shell/file op (XSS + LLM data tests).
- [x] Secrets/stack traces/paths out of client responses and logs (Phase 5–6).
- [x] Production sessions/headers pass automated checks.
- [x] Security events useful and redacted (login/logout; expand later).
- [x] Track A regression suite passes (CI expanded).
- [x] No unrelated dirty files, prod systems, or unauthorized commits (agent discipline).

---

## Execution Order

```text
Tasks 1–2  →  human role-model review  →  Tasks 3–5  →  Tasks 6–8
→  Tasks 9–11  →  Tasks 12–14  →  Tasks 15–16  →  Tasks 17–18
```

---

## Suggested agent prompt (copy-paste)

```text
Execute tasks/NEXT_PLAN_security_hardening.md for Track A Flask CRM only.
Do not touch Track B, chroma_db, graphify-out, node_modules, server.pid, or Stitch exports.
Use synthetic data only. Never print secrets. Coordinate before editing CI or docs/PRODUCTION.md.
Start with route matrix + role model from code; do not invent multi-tenancy.
Prefer failing security tests first, then smallest fixes.
Do not commit or push unless I ask.
```

---

## Plan ladder (handoff order)

| # | Plan | File / note |
|---|------|-------------|
| 1 | Release verification | Done / prior commits |
| 2 | Deprecation modernization | Done / prior work |
| 3 | A11y + frontend performance | Other agent / may have local uncommitted work — use worktree |
| 4 | Data integrity, backup, DR | `tasks/NEXT_PLAN_data_integrity_backup_dr.md` + `docs/BACKUP_RECOVERY_CONTRACT.md` |
| 5 | **Security hardening (this plan)** | `tasks/NEXT_PLAN_security_hardening.md` |
| 6 | Future options | Observability, rate-limit policy tuning, multi-tenant product model (only if product requires) |

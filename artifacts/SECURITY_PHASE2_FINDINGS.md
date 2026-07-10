# Security Phase 2 Findings (Auth + Session)

**Date:** 2026-07-10  
**Branch:** `005-template-replacement`  
**Scope:** Track A only — authentication lifecycle, session cookies, login abuse inspection.

---

## Implemented this phase

| Item | Detail |
|------|--------|
| Default-deny middleware | `register_auth_middleware()` in `app.py`. Env `AUTH_DEFAULT_DENY_ENABLED` default **`1`**. |
| HTML anonymous | 302 → `/auth/login` with relative `session["next_url"]`. |
| API anonymous | 401 JSON `{"error": "Unauthorized. Please log in."}` for `/api/*` or `Accept: application/json`. |
| Public endpoints | `auth.login/register/logout`, `admin_environment.admin_login/logout`, `healthz`, `readyz`, `static`, `favicon`, `main.set_language`. |
| Admin path | Unauth `/admin/*` → admin login (or 401 API). Admin session may also touch `/api/automations`, `/api/admin/*`. |
| Session fixation | Successful login: `session.clear()` then set identity; `session.permanent = True`. |
| Logout | Full `session.clear()`. |
| Open redirect | `_is_safe_next_url` rejects scheme/netloc and `//…` targets. |
| Profile display | `settings_preferences.html` binds `user.full_name` / `name="full_name"` (was wrong `user.name`). |
| Tests | `test_auth_default_deny`, `test_auth_lifecycle`, `test_auth_cookie_hardening` pass. |
| Pytest default | `conftest.py` sets `AUTH_DEFAULT_DENY_ENABLED=0` so legacy UI/CRUD tests keep open access unless they create a fresh app with deny on. |

### How to enable deny in local/prod

```text
AUTH_DEFAULT_DENY_ENABLED=1   # default when unset in create_app
AUTH_DEFAULT_DENY_ENABLED=0   # open CRM (dev / most pytest)
```

---

## Task 4 — Session cookies (verified)

| Setting | Production behavior |
|---------|---------------------|
| `SESSION_COOKIE_HTTPONLY` | `True` |
| `SESSION_COOKIE_SAMESITE` | `Lax` (env override) |
| `SESSION_COOKIE_SECURE` | `True` when `FLASK_ENV=production` (or explicit env) |
| `PERMANENT_SESSION_LIFETIME` | 12h default (`SESSION_LIFETIME_SECONDS`) |
| Secret | Production refuses default `SESSION_SECRET` unless `ALLOW_INSECURE_SECRET=1` |

**Open:** trusted-proxy / `ProxyFix` topology not configured in app factory — defer to deploy docs if TLS terminates at a reverse proxy.

---

## Task 5 — Login abuse / rate limit (findings only)

**Do not enable new rate-limit policy without human approval.**

| Finding | Severity | Evidence |
|---------|----------|----------|
| Flask-Limiter exists but is **not initialized** on the Track A app factory | high | `extensions.init_extensions()` is never called from `app.py` / `create_app`. |
| Login / register have **no** rate-limit or lockout | high | `views/auth.py` — only generic `"Invalid username or password"` flash. |
| Admin login has **no** rate-limit; default password `admin123` via `ADMIN_PASSWORD` | high | `views/admin_environment.py` |
| Property modules define `rate_limit()` helper wrapping `limiter.limit` | medium | Helpers present; limiter may fail or no-op if never `init_app`’d. |
| No account lockout after N failures | medium | No failure counter on User model / session. |
| `X-Forwarded-For` trust not reviewed | medium | Limiter would use `get_remote_address` if wired — untrusted proxy headers can bypass IP limits. |

### Recommended policy (for human approval — not applied)

| Surface | Suggested limit | Notes |
|---------|-----------------|-------|
| `POST /auth/login` | 10 / 15 min / IP | Memory storage OK for single-node; Redis for multi-node (`RATELIMIT_STORAGE_URI`). |
| `POST /auth/register` | 5 / hour / IP | Reduce spam accounts. |
| `POST /admin/login` | 5 / 15 min / IP | Also require strong `ADMIN_PASSWORD` in prod. |
| After limit | 429 + generic message | Same copy as failed login to limit enumeration. |
| Key function | Prefer Flask `request.remote_addr` behind trusted proxy only | Do not trust raw `X-Forwarded-For` without `ProxyFix` allowlist. |

Optional later: progressive delay / temporary lockout by username after 10 failures (needs durable store).

---

## Access model (still needs human confirmation before Tasks 6–8)

From code:

- Authenticated CRM staff share global customer/property/deal data (no per-agent row ownership gate observed on list routes).
- Admin env is separate (`admin_authenticated` session), not the same as `user_role`.
- Default-deny only enforces **authentication**, not object-level **authorization**.

**Before IDOR work:** confirm whether product is global staff CRM vs ownership-scoped multi-agent isolation.

---

## Test commands

```powershell
python -m pytest -q tests/test_auth_default_deny.py tests/test_auth_lifecycle.py tests/test_auth_cookie_hardening.py tests/test_auth_simple.py tests/test_production_config.py tests/test_app_smoke.py
```

Result (this phase): **22 passed**.

---

## Next (Phase 3) — blocked on human

1. Confirm access model (global vs ownership).
2. Deny-first + IDOR tests under that model (Tasks 6–8).
3. Optionally wire limiter + login limits after approving table above.
4. CSRF matrix for state-changing routes (Task 9+).

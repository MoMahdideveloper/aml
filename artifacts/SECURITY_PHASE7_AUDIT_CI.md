# Security Phase 7 — Audit events & CI

**Date:** 2026-07-10

## Security events (`security.events` logger)

| Event | When |
|-------|------|
| `login_success` / `login_failure` | Auth login |
| `logout` | User logout |
| `auth_denial` | Default-deny middleware (login_required / admin_required) |
| `destructive_action` | Successful delete customer/agent/deal/task/property |
| `admin_config_change` | Create/update/delete env var (key only, never value) |

All lines include `request_id=` when request context exists. Sensitive field names redacted to `[REDACTED]`.

## Correlation

- Incoming `X-Request-ID` honored (max 64 chars) or UUID generated.
- Echoed on responses as `X-Request-ID`.

## Login rate limit

| Env | Behavior |
|-----|----------|
| `ENABLE_LOGIN_RATE_LIMIT=1` | Enforce limit |
| `FLASK_ENV=production` | Enforce unless `ENABLE_LOGIN_RATE_LIMIT=0` |
| Default limit | `LOGIN_RATE_LIMIT=10 per 15 minutes` |
| Storage | `RATELIMIT_STORAGE_URI` default `memory://` |

## CI

Core workflow runs security test modules + `scripts/scan_secrets.py`.

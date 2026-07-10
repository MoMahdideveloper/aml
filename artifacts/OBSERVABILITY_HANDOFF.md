# Observability handoff

## What operators get

1. **Correlation:** `X-Request-ID` in/out; JSON logs with `request_id`.  
2. **HTTP RED:** `http_requests_total`, `http_request_duration_seconds_*` by route template / method / status_class.  
3. **Providers:** `external_provider_*` + `event=provider_call` (no prompts).  
4. **Jobs:** `job_events_total` / duration + lifecycle log events.  
5. **Health:** `/healthz` liveness; `/readyz` component map; `/metrics` scrape.  
6. **Runbooks:** `docs/runbooks/`; alert proposals in `docs/ALERTS.md`.

## Env knobs

| Variable | Meaning |
|----------|---------|
| `READYZ_REQUIRE_REDIS=1` | Fail readiness if Redis ping fails |
| (none) | Metrics always in-process; no vendor required |

## Failure-injection proven in tests

- Route exception → 5xx metric + request id  
- DB unavailable → readiness 503, liveness ok  
- Provider timeout → provider metrics/logs without payload  
- Job failure → `job_failed` event  

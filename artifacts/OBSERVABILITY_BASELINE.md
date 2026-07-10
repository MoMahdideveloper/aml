# Observability baseline inventory (Track A)

**Date:** 2026-07-10  
**Branch base:** `242d111` (obs worktree)

## Current signals (before this plan)

| Area | What exists | Gaps |
|------|-------------|------|
| Logging | stdlib `logging`; `utils/security_events.py` key=value events | Not JSON; mixed prose; matching monitor is free-text |
| Correlation | `g.request_id` + `X-Request-ID` on responses (security work) | Not on all service logs; not on jobs/providers |
| Health | `/healthz` liveness JSON; `/readyz` DB `SELECT 1` | No Redis/queue component status; no timeouts on Redis check |
| Monitoring | `services/monitoring_service.py` in-memory deques for matching jobs | Not structured/exportable; unbounded job_id in logs |
| Metrics | No Track A `/metrics` (chatbot has Prometheus — out of scope) | No HTTP RED, no dependency histograms |
| Jobs | Celery beat + `background_matcher` + monitoring_service hooks | No standard job lifecycle event schema |
| Providers | Gemini/Kie timeouts exist | No consistent duration/result telemetry without prompt text |
| Errors | `error_handlers.py` generic client messages | No structured `http_request` failure category on 500 |

## Blind spots

1. Cannot answer p95 latency by route without external APM.  
2. Provider timeouts not aggregated as metrics.  
3. Readiness does not reflect Redis/Celery when used.  
4. Job retries/queue age not first-class.  
5. Duplicate free-text logs in matching vs security events.

## Design choices for this plan

- In-process metrics + Prometheus text (no required extra package).  
- Build on existing `request_id`.  
- Structured `log_event()` shared by HTTP, jobs, providers.  
- Document alerts/runbooks only (no external channel enablement).

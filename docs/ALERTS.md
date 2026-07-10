# Symptom-based alert proposals (not auto-enabled)

**Do not wire production notification channels without human approval.**

Owner default: on-call / Track A maintainer.

| Alert | Severity | Threshold (proposal) | Duration | First diagnostic | Rollback / mitigation | Runbook |
|-------|----------|----------------------|----------|------------------|----------------------|---------|
| Elevated 5xx rate | high | `rate(http_requests_total{status_class="5xx"}[5m]) / rate(http_requests_total[5m]) > 0.05` | 5m | `curl /metrics`; logs `event=http_request` `status_class=5xx` | Scale/restart app; check deploy | [web-errors](runbooks/web-errors.md) |
| p95 latency breach | medium | histogram_quantile 0.95 on `http_request_duration_seconds` > 2s | 10m | `/metrics` by route; slow job events | Disable heavy feature flag; check DB | [slow-routes](runbooks/slow-routes.md) |
| Readiness failure | critical | `/readyz` != 200 | 2m | `curl /readyz`; components.database/redis | Failover DB; verify `DATABASE_URL` | [database-outage](runbooks/database-outage.md) |
| Queue age / job failure | high | `job_events_total{outcome="error"}` spike or matching job age > 15m | 10m | job_failed logs; Celery inspect | Pause beat; drain rematch queue | [job-backlog](runbooks/job-backlog.md) |
| Provider failure spike | medium | `external_provider_calls_total{outcome!="ok"}` ratio > 0.3 | 10m | `event=provider_call` | Fallback provider; circuit-break LLM features | [provider-outage](runbooks/provider-outage.md) |
| Backup/restore drill failure | high | CI drill or `verify_recovery` non-zero | immediate | CI logs; backup artifacts | Re-run drill; block release | See `docs/BACKUP_AND_RECOVERY.md` |

## Notes

- Prefer ratio + duration over single-sample page alerts.
- Never alert on high-cardinality series (per-user, raw URL).

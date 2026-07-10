# Runbook: Redis / queue outage

## Detection

- With `READYZ_REQUIRE_REDIS=1`, readiness fails when Redis down.  
- Celery workers stop consuming; job age grows.

## Triage

1. Check Redis process / managed service.  
2. Inspect Celery broker URL env (redacted).  
3. Review `job_failed` / `job_retried` events.

## Mitigation

- Restart Redis; requeue stuck jobs carefully.  
- Pause beat if thrashing.

## Recovery verification

- Redis ping OK; one beat task completes (`job_succeeded`).

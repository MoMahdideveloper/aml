# Runbook: Job backlog / repeated failures

## Detection

- `job_events_total{outcome="error|retry"}` elevated  
- Matching or SMS queue lag

## Triage

1. Filter logs `event=job_failed` by `job_type`.  
2. Check Redis/broker health.  
3. Confirm workers running.

## Mitigation

- Pause beat schedule; fix poison messages.  
- Scale workers; increase intervals temporarily.

## Recovery verification

- `job_succeeded` resumes; backlog age declining.

# Runbook: Elevated web errors (5xx)

## Detection

- Alert: elevated 5xx rate  
- Logs: `event=http_request` with `status_class=5xx` and shared `request_id`  
- Metrics: `http_requests_total{status_class="5xx"}`

## Triage

1. Confirm blast radius: which `route` labels dominate?  
2. Grab a sample `request_id` from logs; search all lines with that id.  
3. Check `/readyz` components (DB vs Redis).  
4. Review last deploy / migration.

## Mitigation

- Roll back last deploy if correlated.  
- If DB not ready: see database-outage runbook.  
- Disable optional features (matching, LLM extract) via env if providers fault.

## Recovery verification

- 5xx ratio back under threshold for 15m.  
- Synthetic smoke: `/healthz`, login, one list page.

## Evidence

- Request IDs, deploy SHA, `/metrics` snapshot, time window (UTC).

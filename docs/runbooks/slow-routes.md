# Runbook: Slow routes

## Detection

- p95/p99 on `http_request_duration_seconds`  
- Logs: high `duration_ms` on `http_request`

## Triage

1. Identify route templates with elevated latency (not raw paths).  
2. Correlate with job load (`job_duration_seconds`, matching).  
3. Check DB readiness and pool saturation symptoms (query timeouts).

## Mitigation

- Reduce concurrent matching (`MATCHING_INTERVAL_MINUTES`).  
- Temporarily disable heavy list filters.  
- Scale web workers if CPU-bound.

## Recovery verification

- p95 under SLO for 15m; representative UI page load OK.

# Runbook: Database outage

## Detection

- `/readyz` → 503, `components.database.status=error`  
- `/healthz` still 200 (process up)

## Triage

1. `curl -sS localhost:PORT/readyz`  
2. Confirm network / host disk / Postgres status (ops).  
3. Do **not** paste connection strings into tickets.

## Mitigation

- Failover / restore per `docs/BACKUP_AND_RECOVERY.md`.  
- Keep web up for static health; avoid write traffic if possible.

## Recovery verification

- `/readyz` 200; sample CRUD read succeeds.

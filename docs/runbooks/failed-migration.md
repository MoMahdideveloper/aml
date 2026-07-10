# Runbook: Failed migration

## Detection

- Deploy health fails after migrate.  
- App errors on missing columns/tables.

## Triage

1. Capture Alembic revision expected vs actual (ops).  
2. Do not run destructive migrate against prod without approval.

## Mitigation

- Roll back app image to previous revision.  
- Follow DR contract if schema partially applied.

## Recovery verification

- `/readyz` OK; core list pages render.

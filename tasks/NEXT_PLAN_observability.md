# Next Full Plan: Production Observability and Incident Response

**Worktree:** `.claude/worktrees/obs-incident-response`  
**Branch:** `obs/production-telemetry`  
**Base:** `242d111`

## Status

| Phase | Status |
|-------|--------|
| 1 Contract + inventory | Done — `docs/OBSERVABILITY_CONTRACT.md`, `artifacts/OBSERVABILITY_BASELINE.md` |
| 2 Structured request logging | Done — `utils/observability.py` + `app.py` `http_request` JSON events |
| 3 Metrics RED + deps + business | Done — in-process Prometheus `/metrics` |
| 4 Jobs + providers | Done — `timed_job` / `timed_provider`; wired matching monitor, Kie, Gemini, Nominatim |
| 5 Health / alerts / runbooks | Done — `/readyz` components; `docs/ALERTS.md`; `docs/runbooks/*` |
| 6 CI tests | Done — `tests/test_observability.py` in CI list |

## Merge notes

- Do not commit from this agent unless asked.  
- Merge `obs/production-telemetry` → `005-template-replacement` after review.  
- No external alert channels enabled.

## Verify

```powershell
cd .claude/worktrees/obs-incident-response
python -m pytest -q tests/test_observability.py tests/test_health_readiness.py tests/test_production_config.py tests/test_app_smoke.py --tb=short
```

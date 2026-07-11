# Next Full Plan: Production Observability and Incident Response

**Worktree:** `.claude/worktrees/obs-incident-response`  
**Branch:** `obs/production-telemetry` (`f750c3c`)  
**Base:** `242d111`  
**Integration status:** **Integrated** into `005-template-replacement` (ancestor of `c3ac878`). No further merge required.

## Status

| Phase | Status |
|-------|--------|
| 1 Contract + inventory | Done — `docs/OBSERVABILITY_CONTRACT.md`, `artifacts/OBSERVABILITY_BASELINE.md` |
| 2 Structured request logging | Done — `utils/observability.py` + `app.py` `http_request` JSON events |
| 3 Metrics RED + deps + business | Done — in-process Prometheus `/metrics` |
| 4 Jobs + providers | Done — `timed_job` / `timed_provider`; wired matching monitor, Kie, Gemini, Nominatim |
| 5 Health / alerts / runbooks | Done — `/readyz` components; `docs/ALERTS.md`; `docs/runbooks/*` |
| 6 CI tests | Done — `tests/test_observability.py` in CI list |
| 7 Merge to product branch | **Done** — commit already on `005-template-replacement` |

## Merge notes

- Branch tip `f750c3c` is a full ancestor of `005-template-replacement`; do **not** re-merge or cherry-pick.
- Core blobs (`utils/observability.py`, contracts, runbooks, obs tests, instrumented providers) remain identical at product HEAD.
- No external alert channels enabled.
- Do not commit from agents unless a human explicitly requests it.

## Verify (on product branch)

```powershell
# From repo root on 005-template-replacement
python -m pytest -q tests/test_observability.py tests/test_health_readiness.py tests/test_production_config.py tests/test_app_smoke.py --tb=short
```

**Last verification (2026-07-11):** 23 passed; manual `/healthz` 200, `/readyz` 200 ready, `/metrics` 200 Prometheus RED without secrets.

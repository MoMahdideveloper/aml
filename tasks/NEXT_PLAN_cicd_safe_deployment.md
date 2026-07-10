# Next Full Plan: CI/CD, Staging, and Safe Deployment

**Worktree:** `.claude/worktrees/cicd-safe-deploy`  
**Branch:** `cicd/safe-deployment`  
**Base:** `f750c3c`

## Status

| Tasks | Status |
|-------|--------|
| 1–2 Audit + contract | Done — `docs/CICD_PIPELINE_AUDIT.md`, `docs/DELIVERY_CONTRACT.md` |
| 3–5 Deterministic build/image | Done — npm ci, Dockerfile CSS guard, .dockerignore, release-image workflow |
| 6–9 PR gates | Done — matrix suites, PG, Redis, workflow safety, permissions |
| 10–11 Browser/HTTP smoke + metadata | Done — http-smoke job + `release_metadata.py` |
| 12–15 Staging/prod workflows | Done — **manual / dry_run default; no live deploy** |
| 16–18 Rollback + game day | Done — rollback workflow + docs |
| 19–20 Governance + release runbook | Done |

## Merge / commit

Not done by plan author unless requested. No external GitHub settings changed.

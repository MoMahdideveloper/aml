# Next Full Plan: CI/CD, Staging, and Safe Deployment

**Worktree:** `.claude/worktrees/cicd-safe-deploy`  
**Branch:** `cicd/safe-deployment` (`c409335`)  
**Base:** `f750c3c` (observability tip)  
**Integration status:** **Integrated** into `005-template-replacement` (ancestor of `c3ac878`). No further merge required.

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
| 21 Merge to product branch | **Done** — commit already on `005-template-replacement` |

## Merge / commit

- Branch tip `c409335` is a full ancestor of `005-template-replacement`; do **not** re-merge or cherry-pick.
- Workflows, `scripts/ci/*`, and delivery docs remain identical at product HEAD.
- No external GitHub branch-protection settings applied by agents (see `docs/BRANCH_PROTECTION.md` for human checklist).
- Staging/production/rollback workflows stay manual with `dry_run` default; live adapters not configured.
- Do not commit or push unless a human explicitly requests it.

## Verify (on product branch)

```powershell
python -m pytest -q tests/test_cicd_scripts.py --tb=short
python scripts/ci/assert_workflow_safety.py
```

**Last verification (2026-07-11):** 8 cicd script tests passed; `WORKFLOW_SAFETY_OK`.

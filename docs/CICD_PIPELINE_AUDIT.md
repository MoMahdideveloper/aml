# CI/CD pipeline audit (Track A)

**Date:** 2026-07-10  
**Branch base:** `f750c3c`  
**Scope:** `.github/workflows/`, Docker, compose prod profile, locks, migrations.

## Current diagram (before this plan)

```text
push/PR (any branch)
  ├─ css          Node 20, npm ci, build Tailwind, upload artifact
  ├─ lint         Python 3.11, ruff (scoped), black (scoped)
  ├─ core-tests   needs css; pip install requirements; large pytest list;
  │               secret scan; SQLite backup drill
  ├─ postgres-migrations  needs css; PG 16 service; flask db upgrade;
  │                       test_migrations_postgres; pg_dump drill
  └─ full-tests   needs core-tests; continue-on-error; pytest -q all
```

## Findings

| Area | Current | Risk / gap |
|------|---------|------------|
| Triggers | `push: **` + `pull_request` | Every branch push burns minutes; OK for now |
| Permissions | Default (often write-all on older GHA) | Should pin `contents: read` for PR CI |
| Python | 3.11 | Matches `pyproject` / Dockerfile |
| Node | 20 | Matches Dockerfile css stage |
| Caching | pip + npm | Present |
| Locks | `requirements.txt` (uv export), `package-lock.json`, `uv.lock` | Prefer `npm ci` (already used) |
| Quality gates | lint scoped; core tests; PG migrate | Full suite non-blocking |
| Secrets | Synthetic env in workflow | Good — no prod secrets |
| Deploy | **None** | No staging/prod promotion automation |
| Image build | Local `Dockerfile` only | Not built in CI |
| Redis/jobs | Not in CI services | Gap for Celery/always-on |
| Browser smoke | Not in CI | Gap |
| Artifact provenance | CSS artifact only | No immutable app image SHA metadata |
| Permissions / GITHUB_TOKEN | unrestricted defaults | Least-privilege missing |

## Unsafe / missing gates (priority)

1. No production/staging workflow (good that auto-prod is absent; still need **manual** promotion design).  
2. No immutable image build + metadata in CI.  
3. No Redis job smoke.  
4. No browser smoke against production-style boot.  
5. Migration preflight (multiple heads / destructive) only partially covered.  
6. Workflow `permissions` not least-privilege.  
7. `full-tests` continue-on-error can hide debt (keep informational, document).

## Non-goals for this iteration

- Enabling real cloud deploy targets  
- Changing GitHub branch protection settings  
- Strict lint/type entire legacy tree  

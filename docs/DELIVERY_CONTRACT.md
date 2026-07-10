# Track A delivery contract

## Supported runtimes

| Runtime | Version | Pin source |
|---------|---------|------------|
| Python | **3.11** | Dockerfile, workflows, `pyproject.toml` |
| Node | **20** | Dockerfile css stage, workflows |
| Postgres (CI/staging target) | **16** | compose + workflow services |
| Redis (CI/optional) | **7** | compose crm/prod profiles |

Install:

```bash
python -m pip install -r requirements.txt   # committed export from uv
npm ci --ignore-scripts                     # package-lock.json
```

## Required gate sequence

| # | Gate | Command / trigger | Expected | Owner | Timeout | Failure policy |
|---|------|-------------------|----------|-------|---------|----------------|
| 1 | PR opened/updated | GitHub PR / push | workflow starts | platform | — | — |
| 2 | Static lint | `ruff` + `black --check` scoped paths | exit 0 | eng | 5m | block merge |
| 3 | Unit/smoke matrix | pytest groups (smoke, security, recovery, obs) | exit 0 | eng | 10m | block merge |
| 4 | CSS production build | `npm ci` + `npm run build:css` + size check | `tailwind-ph.css` > 10KB | eng | 5m | block merge |
| 5 | Secret scan | `python scripts/scan_secrets.py` | 0 high | eng | 3m | block merge |
| 6 | Postgres migrate | empty DB `flask db upgrade heads` + tests | head revision | eng | 10m | block merge |
| 7 | Redis/job smoke | optional job with redis service | exit 0 | eng | 8m | block merge |
| 8 | Browser/HTTP smoke | `scripts/ci/browser_smoke.py` against app | core routes OK | eng | 8m | block merge |
| 9 | Image build | `docker build` (manual or post-merge) | image tags with SHA | eng | 15m | block release |
| 10 | Release metadata | `scripts/ci/release_metadata.py` | JSON artifact | eng | 2m | block release |
| 11 | Staging deploy | `workflow_dispatch` + staging env | ready+smoke | eng | 20m | stop; no prod |
| 12 | Migration preflight | `scripts/ci/migration_preflight.py` | OK / needs approval | eng | 5m | block deploy |
| 13 | Production promote | **manual** protected env approval | same SHA as staging | eng+approver | 20m | no auto |
| 14 | Post-deploy verify | `scripts/ci/post_deploy_verify.py` | health/ready/smoke | eng | 10m | auto-flag rollback |
| 15 | Monitor window | `/metrics` + logs | no alert breach | on-call | 30–60m | runbook |
| 16 | Rollback | `workflow_dispatch` known-good SHA | service restored | eng | 15m | human |

## Rules

- Ordinary branch **push must never** deploy production.  
- Staging failure **blocks** production job.  
- Production consumes **immutable** image/artifact tagged with git SHA (no rebuild-from-source in prod job).  
- CI credentials are synthetic only.  
- Track B services never deployed by these workflows.  

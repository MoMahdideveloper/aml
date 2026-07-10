# Branch protection recommendations (do not apply without approval)

Recommended for `main` / `005-template-replacement` (or release branch):

| Setting | Recommendation |
|---------|----------------|
| Require PR before merge | Yes |
| Required status checks | `CI / Build CSS`, `CI / Lint`, `CI / Track A tests (smoke)`, `CI / Track A tests (security)`, `CI / Track A tests (recovery)`, `CI / Track A tests (observability)`, `CI / Postgres migrations + readiness`, `CI / Workflow safety` |
| Require branches up to date | Yes |
| Require review count | ≥ 1 |
| Dismiss stale reviews | Yes |
| Restrict force push | Yes |
| Restrict deletions | Yes |
| Require conversation resolution | Yes |
| Allow bypass | Admins only, temporary |
| Signed commits | Optional |

**Do not enable auto-merge to production.** Production uses Environment protection on `deploy-production.yml`.

Workflow permission defaults for PR CI: `contents: read` only.

# Staging Release Rehearsal Evidence

**Date:** 2026-07-14
**Branch:** `rehearsal/staging-release`
**Base commit:** `b0a8552`
**Environment:** Local isolated worktree; plan and dry-run only

## Scope

This evidence records only commands executed during the disposable staging rehearsal gate. No production database, deployment target, live Gemini provider, or external application was contacted.

## Coordinator plan

Command:

```powershell
python scripts/staging_release_rehearsal.py --plan --opt-in `
  --target-db gptvli_rehearsal `
  --target-host localhost `
  --backup-dest .rehearsal/backups `
  --uploads-source .rehearsal/uploads `
  --base-url http://127.0.0.1:55555
```

Result: exit 0. Plan contains seven gates: `workflow_safety`, `migration_preflight`, `release_metadata`, `backup_postgres`, `backup_uploads`, `restore_drill`, and `health_smoke`. Destructive/external gates were marked skipped. Restore plan requires explicit `--backup-dump` for live execution.

## Coordinator dry-run

Command used same target with `--dry-run --opt-in`.

Result: exit 0, `ok=true`, `mode=dry_run`. No subprocesses invoked. Database backup, uploads backup, restore drill, and HTTP smoke remained planned/skipped.

## Automated gates

| Gate | Observed result |
|---|---|
| Rehearsal, backup, retention, CI helpers | **66 passed, 1 skipped** |
| AI form assist | **85 passed, 1 skipped, 8 warnings** |
| Security and production configuration | **40 passed** |
| Workflow static safety | **WORKFLOW_SAFETY_OK** |

Expected skip: live PostgreSQL backup test requires explicitly configured disposable `TEST_DATABASE_URL` and PostgreSQL client tools.

## Not executed

- PostgreSQL backup or restore
- Upload archive or restore
- Alembic upgrade against PostgreSQL
- Running application health/readiness requests
- Browser smoke
- Live Gemini call
- Staging or production deployment
- Production migration
- Commit or push

Reason: no disposable PostgreSQL URL, dump artifact, synthetic uploads directory, or explicitly started local application was configured.

## Remaining gates

1. Configure local disposable PostgreSQL and `TEST_DATABASE_URL`.
2. Seed synthetic-only records and uploads.
3. Run backup, checksum, restore, and migration rehearsal.
4. Start local application against restored target and run health, readiness, auth, CRUD, and mock AI browser smoke.
5. Exercise restore-based rollback and compare synthetic record counts.
6. Obtain human approval before any production backup, migration, feature-flag change, live provider call, deployment, commit, or push.

## Outcome

Plan/dry-run orchestration and automated safety gates passed. Real backup, migration, runtime, browser, and recovery rehearsal remain pending; this report does not claim production readiness.

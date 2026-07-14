# Staging Release Rehearsal (Track A)

**Scope:** Disposable/local targets only. Never points at production.
**No automatic destructive actions.** Live execution requires explicit `--live` + `--opt-in`.

---

## Purpose

A thin coordinator that orchestrates the existing CI/backup/verify scripts in a
safe, documented sequence — to rehearse a release end-to-end before promoting
to staging or production.

Gates in sequence:

1. `workflow_safety` — `scripts/ci/assert_workflow_safety.py`
2. `migration_preflight` — `scripts/ci/migration_preflight.py`
3. `release_metadata` — `scripts/ci/release_metadata.py`
4. `backup_postgres` — `scripts/backup_postgres.py` *(live only; skipped in dry-run)*
5. `backup_uploads` — `scripts/backup_uploads.py` *(live only; skipped in dry-run)*
6. `restore_drill` — `scripts/restore_postgres.py` *(live only; skipped in dry-run)*
7. `health_smoke` — `scripts/ci/browser_smoke.py` *(live only; dry-run mock)*

---

## Safety contracts

- **Refuses** production-looking hosts (`rds.amazonaws.com`, `azure.com`,
  `cloudsql`, hostnames containing `production`, `prod-db`).
- **Refuses** system DB names (`postgres`, `template0`, `template1`).
- **Refuses** `base_url` pointing outside `localhost`/`127.0.0.1` in live mode.
- **Requires** `--opt-in` flag; construction raises `RehearsalRefused` without it.
- **Requires** `--live` flag for any subprocess execution; `run()` without it raises
  `RehearsalRefused`.
- **Never** embeds passwords in plan output or report.
- **No automatic cleanup** — target DB and backup artifacts are left for human review.

---

## Plan mode (no external binaries required)

```powershell
python scripts/staging_release_rehearsal.py `
  --plan `
  --opt-in `
  --target-db  gptvli_rehearsal_drill `
  --target-host 127.0.0.1 `
  --backup-dest .\backups\rehearsal `
  --uploads-source .\static\uploads `
  --base-url http://127.0.0.1:8000
```

Prints JSON step list. No subprocesses are invoked.

---

## Dry-run mode (no external binaries required)

```powershell
python scripts/staging_release_rehearsal.py `
  --dry-run `
  --opt-in `
  --target-db  gptvli_rehearsal_drill `
  --target-host 127.0.0.1 `
  --backup-dest .\backups\rehearsal `
  --uploads-source .\static\uploads `
  --base-url http://127.0.0.1:8000
```

Returns JSON report with `mode=dry_run`, all destructive steps flagged as skipped.
Exit 0 on success.

---

## Live execution (requires disposable local DB + running app)

Prerequisites:
- Local Postgres running on `127.0.0.1` with a disposable instance
- `DATABASE_URL` or `PG*` env vars pointing at it (never production)
- Flask app running at `--base-url`

```powershell
$env:DATABASE_URL = "postgresql://gptvli:REDACTED@127.0.0.1:5432/gptvli_drill"

python scripts/staging_release_rehearsal.py `
  --live `
  --opt-in `
  --target-db  gptvli_rehearsal_drill `
  --target-host 127.0.0.1 `
  --backup-dest .\backups\rehearsal `
  --uploads-source .\static\uploads `
  --base-url http://127.0.0.1:8000
```

The coordinator:
1. Runs each gate in sequence via the existing scripts.
2. Records exit code, sanitized stdout/stderr for every gate.
3. Reports overall `ok: true/false`.
4. Does **not** switch `DATABASE_URL` — that requires human approval.
5. Does **not** clean up the restore target — preserved for inspection.

---

## Evidence record template

After a live run, capture:

| Item | Value |
|------|-------|
| Run date (UTC) | |
| Git SHA | |
| workflow_safety | PASS / FAIL |
| migration_preflight | PASS / FAIL |
| release_metadata sha | |
| backup_postgres size | |
| backup_postgres sha256 | |
| restore_drill target_db | |
| restore_drill ok | PASS / FAIL |
| health_smoke /healthz | PASS / FAIL |
| health_smoke /readyz | PASS / FAIL |
| Notes / gaps | |

---

## Tests

```powershell
python -m pytest tests/test_staging_release_rehearsal.py -v --tb=short
```

47 tests — no network, DB, paid API, or destructive subprocess calls.
All live execution injected via `FakeRunner`.

---

## Related docs

- `docs/BACKUP_AND_RECOVERY.md` — backup/restore runbook
- `docs/RELEASE_RUNBOOK.md` — staging/production promotion steps
- `docs/DEPLOYMENT_GAME_DAY.md` — drill record template
- `scripts/ci/migration_preflight.py` — offline migration safety scan
- `scripts/ci/browser_smoke.py` — health/readiness probes

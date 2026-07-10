# Backup and Recovery Runbook (Track A)

**Scope:** Flask CRM only. Synthetic/disposable drills first.  
**Contract:** `docs/BACKUP_RECOVERY_CONTRACT.md`  
**Never commit dumps, credentials, or customer data.**

---

## SQLite (local / disposable)

### Backup

```powershell
# Explicit source + dest-dir required (no hidden production defaults)
python scripts/backup_sqlite.py `
  --source ".\real_estate_crm.db" `
  --dest-dir ".\backups" `
  --json
```

Behavior:

- Uses SQLite **online backup API** (not a raw live file copy).
- Writes timestamped `gptvli-sqlite-YYYYMMDDTHHMMSSZ.db` via a `.tmp` file, then renames after `PRAGMA integrity_check`.
- Writes `*.db.sha256` sidecar.
- Compares user-table row counts source vs backup.
- Exit code nonzero on failure; refuses Postgres URLs and production-looking paths.

### Restore (new target first)

```powershell
python scripts/restore_sqlite.py `
  --backup ".\backups\gptvli-sqlite-….db" `
  --destination ".\backups\restore-drill.db"
```

Overwrite existing destination only with `--force` (creates `.rollback-*` copy first).

```powershell
python scripts/restore_sqlite.py `
  --backup ".\backups\gptvli-sqlite-….db" `
  --destination ".\real_estate_crm.db" `
  --force `
  --expected-alembic "k6l7m8n9o0p1"
```

### Verify

```powershell
python scripts/verify_recovery.py `
  --database ".\backups\restore-drill.db" `
  --expected-alembic "k6l7m8n9o0p1"
# optional app probe (sets disposable SESSION_SECRET):
python scripts/verify_recovery.py --database ".\backups\restore-drill.db" --check-readyz
```

Output is JSON (counts/status only — no customer row content).

---

## PostgreSQL (disposable drill)

**Connection only from environment** (`DATABASE_URL` or `PGHOST`/`PGUSER`/`PGDATABASE`/`PGPASSWORD`).  
This project’s wrapper **never puts the password on the command line**.

### Backup (custom format `-Fc`)

```powershell
# Disposable instance only — do not point at production without ALLOW_PROD_BACKUP=1 + approval
$env:DATABASE_URL = "postgresql://gptvli:REDACTED@127.0.0.1:5432/gptvli_drill"
python scripts/backup_postgres.py --dest-dir .\backups --json
# Produces: gptvli-postgres-*.dump + .sha256 + .meta.json
# Verifies with: pg_restore --list
```

Requires `pg_dump` and `pg_restore` on PATH.

### Restore runbook (fresh DB only)

1. **Stop application writes** (scale down web/workers).
2. Verify archive checksum/metadata and `pg_restore --list`.
3. Create **new** disposable database (do not restore over live).
4. Prefer the guarded wrapper:

```powershell
$env:DATABASE_URL = "postgresql://gptvli:REDACTED@127.0.0.1:5432/postgres"
python scripts/restore_postgres.py `
  --dump ".\backups\gptvli-postgres-….dump" `
  --target-db "gptvli_restore_drill" `
  --drop-target-if-exists
```

   Manual alternative: `pg_restore --no-password -d <newdb> archive.dump` with `PG*` env vars only.

5. Schema/integrity checks + Alembic `flask db current` with `DATABASE_URL` pointing at the **new** DB.
6. Smoke: `/healthz`, `/readyz`, login, one list page.
7. **Switch application `DATABASE_URL` only after human approval.**
8. Keep prior DB/volume as rollback until sign-off.

---

## Common failures

| Symptom | Action |
|---------|--------|
| `integrity_check failed` | Discard artifact; re-run backup; investigate disk |
| Checksum mismatch | Re-copy archive; do not restore |
| Destination exists | Use new path or `--force` (SQLite) |
| Alembic mismatch | Restore matching revision dump or upgrade disposable DB deliberately |
| Postgres tools missing | Install client tools; fail closed |

## Escalation

- Production restore: product owner + ops approval (see contract).
- Suspected ransomware/corruption: isolate volumes; restore to disposable first.

## Evidence after drill

Record: duration, backup size, SHA-256, Alembic revision, verifier JSON `ok`, smoke result.

---

## Uploads (media files)

```powershell
python scripts/backup_uploads.py --source-dir .\static\uploads --dest-dir .\backups --json
```

Restore order: **database first**, then extract archive into upload root. Pair DB and uploads artifacts by timestamp.

## Retention (scheduler-ready, not auto-enabled)

```powershell
# List what would be deleted (default dry-run)
python scripts/backup_retention.py --dir .\backups --keep-count 7 --glob "gptvli-*.db" --json
# Actually delete (explicit)
python scripts/backup_retention.py --dir .\backups --keep-count 7 --execute
```

Example Task Scheduler / cron: run backup then retention; lock with a single-instance mutex if needed.  
**Encrypted storage:** store dumps off-host (object storage / encrypted disk); rotate access keys; never commit archives.

## Alert hook contract (optional)

Backup scripts exit `0` on success and nonzero on failure. Wrap in:

```text
python scripts/backup_sqlite.py ... || notify_ops "sqlite backup failed"
```

Do not embed webhook secrets in the repo.

## Tests

```powershell
python -m pytest -q tests/test_backup_sqlite.py tests/test_restore_sqlite.py tests/test_verify_recovery.py tests/test_backup_postgres.py tests/test_backup_retention.py --tb=short
```

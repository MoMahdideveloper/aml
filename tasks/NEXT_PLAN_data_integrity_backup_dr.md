# Next Full Plan: Data Integrity, Backup, and Disaster Recovery

**Give this plan to another agent after** release-readiness, deprecation modernization, and accessibility/frontend-performance work are finished or isolated.

**This scope is independent** from UI, accessibility, performance, and Pydantic/datetime deprecation work. Prefer an isolated git worktree if other agents still touch templates/tests.

---

## Mission

Make Track A Flask CRM **recoverable** after database corruption, accidental deletion, failed migration, or bad deploy. Deliver a **tested** backup and restore workflow for:

| Environment | Primary store | Also protect |
|-------------|---------------|--------------|
| Local/dev | SQLite (`real_estate_crm.db` / `DATABASE_URL`) | optional `static/uploads/` |
| Production | PostgreSQL via `DATABASE_URL` | upload volume (`uploads_data` / `static/uploads`) |

Align with existing runbook notes in `docs/PRODUCTION.md` (health/ready probes, migration fail-closed entrypoint, rollback sketch) without inventing a second ops stack.

---

## Hard Boundaries

- **Track A only.** Do not modify `api/`, `matcher/`, `ingestor/`, or `chatbot/`.
- Do **not** access, copy, overwrite, or **restore production data during development**.
- Use **synthetic disposable databases only** for all drills.
- **Never** commit database dumps, credentials, `.env`, customer data, or backup archives.
- **Never touch** dirty generated paths: `chroma_db/`, `graphify-out/`, `node_modules/`, `server.pid`, Stitch exports under `stitch_kpi_performance_dashboard/`.
- Do **not** run destructive restore or downgrade without **explicit target verification**.
- **Coordinate with the release agent** before modifying migrations, CI, or `docs/PRODUCTION.md`.
- Do **not** commit, push, delete `templates/_archive/`, or drop production volumes without explicit approval.
- Prefer **scripts + docs + tests** over new product features or admin UIs.
- No dependency upgrades unless a measured restore failure requires one tool version pin.
- **Do not start Phase 2 implementation until Checkpoint 1 recovery contract is approved** (see `docs/BACKUP_RECOVERY_CONTRACT.md`).

---

## Context (current repo facts)

- Dev default DB: SQLite (`sqlite:///real_estate_crm.db` or instance path); prod: Postgres `DATABASE_URL`.
- Migrations: Flask-Migrate / Alembic under `migrations/`; Docker entrypoint can run `flask db upgrade heads` with fail-closed retries (`RUN_MIGRATIONS`).
- Health: `GET /healthz` (liveness), `GET /readyz` (DB readiness).
- Uploads: property media under static uploads / Docker volume `uploads_data`.
- Production docs already list “Backups for DATABASE_URL / upload volume” as a checklist item and a high-level rollback path — this plan makes that **executable and tested**.

---

## Architecture Decisions

1. **Backup is offline-consistent for SQLite** (file copy under lock or `VACUUM INTO` / SQLite backup API), not a mid-write OS copy of a live file without care.
2. **Postgres backups use logical dumps** (`pg_dump` custom or plain SQL) plus optional base-backup later — start with logical dump restore drills.
3. **Uploads are a separate artifact** from DB dumps; restore must document order: restore DB → restore uploads → migrate if needed → probe health.
4. **Restore always targets a disposable database first**; production restore is a human-gated runbook step.
5. **Migration safety**: document pre-migrate backup, and practice restore + re-upgrade on disposable DB after intentional failure.
6. **No silent auto-restore** in the app process; backups are ops tooling, not a background job that overwrites data.

---

## Dependency Graph

```text
Inventory DB paths + upload paths + env matrix
    │
    v
Backup scripts (SQLite + Postgres) + checksums + retention policy
    │
    v
Restore scripts to disposable targets + smoke verification
    │
    v
Automated restore drill tests (CI-safe, disposable only)
    │
    v
Runbook: backup schedule, pre-migrate, incident restore, RPO/RTO notes
    │
    v
Optional: CI scheduled backup dry-run / upload artifact (report-only)
```

---

## Phase 1: Recovery Requirements

### Task 1: Map persistent data

Inventory all Track A persistence:

- SQLAlchemy tables and relationships.
- Uploaded property/customer media.
- Generated exports or reports.
- Redis data and whether it is disposable.
- Environment configuration required for recovery.
- Scheduled jobs that can recreate derived data.

**Likely files:** `sqlalchemy_models.py`, `app.py`, `services/`, `repositories/`, `docs/PRODUCTION.md`, `docker-compose.yml`.

**Acceptance criteria:**
- [x] Every persistent asset classified as **authoritative**, **derived**, **cache**, or **secret**.
- [x] Recovery order documented.
- [x] No data copied.

**Deliverable:** `docs/BACKUP_RECOVERY_CONTRACT.md` §1.

### Task 2: Define recovery objectives

Document recommended targets:

- RPO / RTO
- Backup frequency and retention
- Encryption and access-control requirements
- Restore ownership and approval process

**Acceptance criteria:**
- [x] SQLite local policy and PostgreSQL production policy separated.
- [x] Assumptions clearly marked for human approval.

**Deliverable:** `docs/BACKUP_RECOVERY_CONTRACT.md` §2.

---

## Checkpoint 1

- [x] Persistence map complete.
- [x] RPO/RTO proposal ready for human review.
- [x] **No implementation started before recovery contract is understood / approved.**
- [ ] **Human approval of assumptions in §2** (blocks Phase 2).

---

## Phase 2: Backup tooling

### Task 3: SQLite backup script

**Description:** Add a safe, idempotent script to snapshot the configured SQLite file.

**Acceptance criteria:**
- [x] Explicit `--source` / `--dest-dir`; refuses Postgres URLs and prod-looking paths.
- [x] Timestamped artifact under gitignored `backups/` (or any explicit dir).
- [x] SQLite online backup API + atomic `.tmp` then rename.
- [x] SHA-256 sidecar + integrity_check + row-count match.
- [x] Nonzero exit on failure; tests in `tests/test_backup_sqlite.py`.

**Verification:**
```powershell
$env:DATABASE_URL = "sqlite:///real_estate_crm.db"
python scripts/backup_sqlite.py
# file + .sha256 exist under backups/
```

**Dependencies:** Task 1.

**Likely files:** `scripts/backup_sqlite.py`, `backups/.gitignore`, `.gitignore`.

**Estimated scope:** S.

### Task 4: PostgreSQL backup script

**Description:** Wrap `pg_dump` for `DATABASE_URL=postgresql://...`.

**Acceptance criteria:**
- [ ] Parses/uses `DATABASE_URL`; refuses SQLite.
- [ ] Supports custom format (`-Fc`) or plain SQL; document restore command for the chosen format.
- [ ] Checksum sidecar; timestamped name; gitignored output dir.
- [ ] Clear error if `pg_dump` missing.

**Verification:** Against **local disposable** Postgres only (Docker service or CI service), never prod.

**Dependencies:** Task 1.

**Likely files:** `scripts/backup_postgres.py` or `scripts/backup_postgres.ps1` + `.sh`, `docs/BACKUP_AND_RECOVERY.md`.

**Estimated scope:** M.

### Task 5: Uploads backup helper

**Description:** Archive `static/uploads` (or configured upload root) as a separate tarball/zip with checksum.

**Acceptance criteria:**
- [ ] Empty upload dir is a successful empty archive or explicit skip message.
- [ ] Does not walk `node_modules`, `chroma_db`, or Stitch trees.
- [ ] Documented pairing rule: restore DB then uploads.

**Dependencies:** Task 1.

**Likely files:** `scripts/backup_uploads.py`, docs.

**Estimated scope:** S.

---

## Checkpoint B: Backups produce artifacts

- [ ] SQLite backup works on local CRM DB path.
- [ ] Postgres backup works on disposable instance.
- [ ] Uploads archive works or cleanly skips empty tree.
- [ ] No secrets or dump files staged for commit.

---

## Phase 3: Restore tooling and drills

### Task 6: SQLite restore to disposable target

**Description:** Restore a backup file into a **new** SQLite path (never overwrite default without `--force` + confirmation flag).

**Acceptance criteria:**
- [ ] Verifies checksum before restore.
- [ ] Default target is a disposable path under `backups/restore-test-*.db` or temp dir.
- [ ] Overwrite of live path requires explicit `--force` and fails closed otherwise.
- [ ] After restore, `FLASK_APP=app.py` + `DATABASE_URL=...` app can `/readyz` or open a test client query.

**Verification:** Automated test using temp DB only.

**Dependencies:** Task 3.

**Likely files:** `scripts/restore_sqlite.py`, `tests/test_backup_restore_sqlite.py`.

**Estimated scope:** M.

### Task 7: Postgres restore drill on disposable DB

**Description:** Document and script restore of dump into empty disposable database.

**Acceptance criteria:**
- [ ] Steps: create empty DB → restore dump → `flask db current` / app ready.
- [ ] Script refuses production-looking hostnames unless `ALLOW_PROD_RESTORE=1` **and** human flag (default off).
- [ ] At least one automated or CI job restores into the workflow Postgres service.

**Dependencies:** Task 4.

**Likely files:** `scripts/restore_postgres.py`, `.github/workflows/tests.yml` (optional job) or docs-only if tooling unavailable on Windows agent — prefer CI Linux job.

**Estimated scope:** M.

### Task 8: Migration failure recovery drill

**Description:** On disposable DB, prove: backup → apply migration → simulated failure → restore backup → app healthy.

**Acceptance criteria:**
- [ ] Written drill for snapshot migration `j5k6l7m8n9o0` / head `k6l7m8n9o0p1` on empty disposable DB.
- [ ] Note: `downgrade -1` from merge heads can be ambiguous — use **explicit revision** targets.
- [ ] Document pre-`flask db upgrade` backup as mandatory for production.

**Dependencies:** Tasks 3–7.

**Estimated scope:** S–M.

---

## Checkpoint C: Restore proven on disposable systems

- [ ] SQLite restore test green.
- [ ] Postgres restore drill green or documented CI job green.
- [ ] Migration recovery path written with explicit revisions.
- [ ] Production remains untouched.

---

## Phase 4: Runbooks and app safety hooks (minimal)

### Task 9: Operator runbook

**Description:** Single place for humans and agents.

**Acceptance criteria:**
- [ ] Sections: daily backup, pre-deploy backup, restore SQLite, restore Postgres, restore uploads, post-restore smoke (`/healthz`, `/readyz`, login, one list page).
- [ ] Cross-link from `docs/PRODUCTION.md` checklist item “Backups…”.
- [ ] Explicit “do not commit dumps”; retention; where files live.

**Dependencies:** Checkpoints B–C.

**Likely files:** `docs/BACKUP_AND_RECOVERY.md`, `docs/PRODUCTION.md`.

**Estimated scope:** S.

### Task 10: Optional pre-migrate guard (dev-friendly)

**Description:** Only if low-risk: Makefile/script target `make backup-db` / `scripts/pre_migrate_backup.py` that agents/docs call before upgrades.

**Acceptance criteria:**
- [ ] Does not run automatically inside `create_app()`.
- [ ] Wired in docs and optionally `Makefile` / `scripts/up-prod.ps1` comments.
- [ ] Still never backs up production without env pointing at intentional URL.

**Dependencies:** Tasks 3–4.

**Estimated scope:** XS–S.

---

## Phase 5: Automation and handoff

### Task 11: CI quality gate (lightweight)

**Description:** Add tests that never need real prod credentials.

**Acceptance criteria:**
- [ ] SQLite backup+restore round-trip test in pytest (temp paths).
- [ ] Optional Postgres job using existing workflow service container.
- [ ] Heavy full-volume restore remains manual/report-only.

**Verification:**
```bash
pytest -q tests/test_backup_restore_sqlite.py --tb=short
# if added:
# pytest -q tests/test_backup_restore_postgres.py --tb=short
```

**Dependencies:** Tasks 6–7.

**Likely files:** `tests/test_backup_restore_sqlite.py`, `.github/workflows/tests.yml`.

**Estimated scope:** M.

### Task 12: Evidence report and planning docs

**Description:** After verification, update handoff docs.

**Acceptance criteria:**
- [ ] Report: commands, artifact names, restore success, remaining risks, RPO/RTO.
- [ ] `tasks/todo.md` / plan status only after evidence.
- [ ] No unrelated dirty files staged.

**Dependencies:** All prior.

**Estimated scope:** S.

---

## Final Verification

```powershell
# Unit/integration (disposable only)
python -m pytest -q tests/test_backup_restore_sqlite.py --tb=short

# Existing Track A gates still green (do not regress product)
python -m pytest -q tests/test_platinum_heritage_ui.py tests/test_app_smoke.py tests/test_simple.py tests/test_template_replacement.py --tb=short
python -m pytest -q tests/test_dashboard_trends.py tests/test_dashboard_template.py

# Manual disposable drill
# 1) backup sqlite/postgres
# 2) restore to new target
# 3) DATABASE_URL=<restored> python -c "from app import create_app; ..."
# 4) curl /healthz /readyz against disposable run if server started
```

---

## Definition of Done

- [ ] SQLite and Postgres backup scripts exist, documented, gitignore-safe.
- [ ] Restores proven on **disposable** targets with checksum verification.
- [ ] Uploads backup path documented and scripted.
- [ ] Pre-migrate backup is part of the production runbook.
- [ ] CI covers at least SQLite round-trip; Postgres preferred when service available.
- [ ] Track A product tests still pass.
- [ ] Production data never modified without explicit human approval.
- [ ] Unrelated dirty trees untouched; no secrets committed.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Overwriting live DB during restore | Critical | Default disposable targets; `--force` gated; refuse prod hosts |
| Inconsistent SQLite file copy | High | Use backup API / documented lock approach |
| Dump contains PII in CI artifacts | High | Keep artifacts local/gitignored; no upload of real dumps |
| Merge-head Alembic downgrade ambiguity | Medium | Explicit revision IDs in drills |
| False confidence without upload restore | Medium | Pair DB + uploads in runbook smoke |

---

## Out of scope (later plans)

- Multi-region replication, PITR, WAL archiving (can be a follow-up plan).
- Encrypting backups at rest with KMS (document as recommendation only unless requested).
- Track B / Neo4j / Chroma recovery.
- Changing CRM product features or UI.

---

## Suggested agent prompt (copy-paste)

```text
Execute tasks/NEXT_PLAN_data_integrity_backup_dr.md for Track A Flask CRM only.
Do not touch Track B, chroma_db, graphify-out, node_modules, server.pid, or Stitch exports.
Never restore or dump a production database without explicit approval.
Prefer disposable SQLite/Postgres only. Implement scripts + tests + docs/BACKUP_AND_RECOVERY.md.
Do not commit or push unless I ask. Update tasks/todo.md only after evidence.
```

---

## Parallel tracks (if multiple agents)

| Plan | Status / note |
|------|----------------|
| Release verification | Likely done — do not re-litigate unless regressions |
| Deprecation modernization | Likely done |
| A11y + frontend performance | Separate agent; may still have uncommitted work — use worktree |
| **This plan: Backup / DR** | **Next independent mission** |
| Future: Auth hardening / secrets rotation | After DR baseline |
| Future: Observability (structured logs, metrics) | After DR baseline |

# Track A — Backup & Recovery Contract (Phase 1)

**Status:** Draft for human approval — **no backup/restore implementation started beyond this contract.**  
**Date:** 2026-07-10  
**Scope:** Flask CRM (Track A) only. Track B matching stack is out of scope.

---

## Hard boundaries (operators & agents)

- Do **not** access, copy, overwrite, or restore **production** data during development.
- Use **synthetic disposable databases only** for drills.
- Never commit database dumps, credentials, `.env`, customer data, or backup archives.
- Do not touch dirty generated trees: `chroma_db/`, `graphify-out/`, `node_modules/`, `server.pid`, Stitch exports.
- Do not run destructive restore or downgrade without explicit target verification.
- **Coordinate with release agent** before modifying migrations, CI, or `docs/PRODUCTION.md`.

---

## 1. Persistent data map

### 1.1 Classification legend

| Class | Meaning | Recover by |
|-------|---------|------------|
| **Authoritative** | Source of truth for CRM; loss = real business data loss | Backup + restore |
| **Derived** | Can be rebuilt from authoritative data + jobs | Recompute after restore |
| **Cache** | Disposable; improves speed only | Ignore or flush |
| **Secret** | Credentials/config; not in DB dumps | Secret store / `.env` (never in git) |
| **Out of scope** | Track B / experimental | Not part of CRM DR |

### 1.2 Authoritative — SQLAlchemy / Postgres or SQLite

Primary store: `DATABASE_URL` (dev default `sqlite:///real_estate_crm.db`; prod Postgres via compose `db` volume `postgres_data`).

| Table | Domain | Notes |
|-------|--------|--------|
| `properties` | Listings | Core inventory |
| `property_images` | Media metadata | Filenames point at upload store |
| `property_activity_log` | Audit | Listing activity |
| `agents` | People | CRM agents |
| `customers` | People | Clients / prefs |
| `customer_groups` | People | Grouping |
| `customer_opportunity_briefs` | Matching prefs | Multi-need briefs |
| `deals` | Pipeline | Offers / stages |
| `tasks` | Ops | Assignments |
| `users` | Auth | Login identities |
| `builders` | Listings meta | Optional builder records |
| `contact_reveals` | Privacy/audit | Reveal events |
| `public_property_submissions` | Intake | Public submissions |
| `open_house_checkins` | Events | Kiosk check-ins |
| `client_messages` | Messaging | Client thread history |
| `sms_outbound_messages` | Messaging | Outbound SMS log |
| `property_favorites` | UX prefs | Saved properties |
| `agent_notifications` | Alerts | Match alerts |
| `property_matches` | Matching results | Can be regenerated but often treated as business history |
| `property_embeddings` | Vectors in SQL | Regenerable from properties + AI keys |
| `matching_job_runs` | Ops history | Job telemetry |
| `rematch_queue` | Work queue | Pending work; regenerable |
| `automation_rules` | Config | Automation definitions |
| `automation_audit_log` | Audit | Rule run history |
| `environment_variables` | Runtime config in DB | Sensitive values possible — treat carefully |
| `environment_change_log` | Audit | Env changes |
| `dashboard_stat_snapshots` | Analytics | MoM trends; regenerates over time if missing (neutral trends) |
| `suggestion_items`, `analysis_templates`, `analysis_reports` | Analysis | Product analysis features |
| `property_ai_history`, `model_performance_metrics`, `ai_metadata` | AI ops | History/metrics |
| `sync_state` | Integration state | Sync cursors |

**Relationships (recovery implication):** Deals depend on property/customer/agent FKs; property images depend on properties; notifications/matches depend on properties/customers/agents. Restore must load a **consistent single dump**, not table-by-table partial files.

### 1.3 Authoritative — file media

| Path / volume | Class | Notes |
|---------------|-------|--------|
| `static/uploads/` (local) | **Authoritative** | Property media binary files |
| Docker volume `uploads_data` → `/app/static/uploads` | **Authoritative** | Prod compose |

DB rows in `property_images` without files (or files without rows) = partial corruption. Restore order: **DB first, then uploads**, then smoke-check media URLs.

### 1.4 Derived (rebuild after DB restore)

| Asset | How to recreate |
|-------|-----------------|
| `property_matches` / scores | Always-on rematch / matching sweep (Celery beat + worker) |
| `rematch_queue` pending rows | Enqueue/rematch jobs |
| `property_embeddings` | Re-index via vector/embedding services when API keys present |
| `dashboard_stat_snapshots` | Accumulates daily on dashboard load; history gap → neutral trends until snapshots exist |
| `agent_notifications` | May re-fire on new/improved matches (dedupe rules apply) |
| Built CSS `static/css/tailwind-ph.css` | `npm run build:css` (artifact, not customer data) |

### 1.5 Cache / disposable

| Asset | Class | Notes |
|-------|-------|--------|
| Redis (`REDIS_URL`, volume `redis_data`) | **Cache + broker** | Celery broker/results, rate limits, optional cache. **AOF enabled** in compose but **CRM can restart without Redis data** for core CRUD. Treat as **non-authoritative** for CRM recovery unless message durability is later required. |
| In-process / app memory | Disposable | — |
| Flask session cookies | Disposable | Users re-login |

### 1.6 Secrets (never in backups committed to git)

| Secret | Source |
|--------|--------|
| `SESSION_SECRET` | Env / secret store |
| `DATABASE_URL` / `POSTGRES_PASSWORD` | Env |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Env |
| SMS provider credentials | Env |
| Any values in `environment_variables` table | DB — **authoritative config**; exclude from shared dump samples if redacting |

### 1.7 Out of scope for Track A DR

| Asset | Why |
|-------|-----|
| Neo4j volumes (`matching` profile) | Track B experimental |
| `api/`, `matcher/`, `ingestor/`, `chatbot/` data | Track B |
| `chroma_db/` | Local vector store; optional/dev; not prod CRM source of truth |
| `graphify-out/`, Stitch exports | Tooling artifacts |

### 1.8 Environment required to run after restore

Minimum:

- `FLASK_ENV` / `SESSION_SECRET` / `DATABASE_URL`
- Prod: `USE_TAILWIND_CDN=0`, `ENABLE_CSRF=1`, built CSS present
- Optional for full AI/match: `REDIS_URL`, Celery worker+beat, `GOOGLE_API_KEY`
- Probes: `/healthz`, `/readyz`

### 1.9 Recommended recovery order

1. Provision empty disposable target (SQLite file or Postgres DB).  
2. Restore **database dump** (single consistent backup).  
3. Run migrations only if dump is from older revision (`flask db upgrade heads`) — prefer dump already at head.  
4. Restore **uploads** archive into upload root.  
5. Configure env secrets (not from dump).  
6. Start app; verify `/healthz` + `/readyz`.  
7. Smoke: login → dashboard → properties (image) → deals → tasks.  
8. Optionally start Redis/Celery and rematch to rebuild derived match data.

---

## 2. Recovery objectives (proposal — **needs human approval**)

Assumptions are marked **[ASSUMPTION]**. Change before treating as policy.

### 2.1 Local / SQLite development

| Objective | Proposed default | Notes |
|-----------|------------------|--------|
| **RPO** | **[ASSUMPTION] 24 hours** or last intentional backup | Devs may lose uncommitted local edits |
| **RTO** | **[ASSUMPTION] 30 minutes** | Restore file + point `DATABASE_URL` |
| Frequency | Before risky migrations / end of day if valuable data | Manual is OK |
| Retention | Last **7** local dumps | Gitignored directory only |
| Encryption | Optional for local | Disk encryption of laptop recommended |
| Approval | Developer owns local restores | Never point scripts at prod |

### 2.2 Production / PostgreSQL

| Objective | Proposed default | Notes |
|-----------|------------------|--------|
| **RPO** | **[ASSUMPTION] ≤ 24 hours** | Daily dump; tighten to 1h if cron+object storage added later |
| **RTO** | **[ASSUMPTION] ≤ 4 hours** | Includes human approval + DNS/app restart |
| Frequency | Daily automated + **mandatory** before migrate/deploy | Document in runbook |
| Retention | **[ASSUMPTION]** 7 daily + 4 weekly | Off-host storage (not only same VM) |
| Encryption | **[ASSUMPTION]** At-rest on backup storage; transit TLS | Keys outside dump |
| Access | Ops only; dumps contain **PII** (customers, agents) | No dumps in git/CI artifacts from real prod |
| Approval | **Human required** for any restore to a shared/prod host | Script must refuse prod hosts by default |

### 2.3 What “full CRM restore” means

| Included | Excluded unless requested |
|----------|---------------------------|
| Postgres/SQLite CRM schema + rows | Neo4j / Track B |
| `static/uploads` / `uploads_data` | `chroma_db` |
| Ability to serve UI after env secrets applied | Historical Redis Celery results |

### 2.4 Ownership and approval process **[ASSUMPTION]**

| Event | Owner | Approval |
|-------|-------|----------|
| Daily backup job | Ops / deploy owner | None (automated) |
| Pre-migrate backup | Engineer running migrate | Peer optional |
| Restore to staging/disposable | Engineer | None if disposable |
| Restore to production | Ops + product owner | **Explicit written approval** |
| Downgrade Alembic on shared DB | Engineer | Explicit revision + approval |

---

## 3. Checkpoint 1 status

| Item | Status |
|------|--------|
| Persistence map complete | **Yes** (this doc §1) |
| RPO/RTO proposal ready for human review | **Yes** (this doc §2) — defaults are assumptions |
| No backup/restore implementation started | **Yes** — wait for approval of this contract |
| No production data accessed | **Yes** |
| No dumps or secrets committed | **Yes** |

### Human decisions needed before Phase 2 (scripts)

1. Accept or revise RPO/RTO for prod (24h / 4h).  
2. Confirm Redis is non-authoritative for DR.  
3. Confirm whether `property_matches` / embeddings are “nice to restore” vs always rebuild.  
4. Approve gitignored `backups/` directory convention and retention numbers.  
5. Name who may approve production restore.

---

## 4. Commands used for this inventory (read-only)

```text
# Model tables: grep __tablename__ sqlalchemy_models.py
# Compose volumes: docker-compose.yml profiles prod/crm
# Env template: .env.example
# Production notes: docs/PRODUCTION.md
```

No databases were dumped or copied for this phase.

---

## 5. Implementation progress

| Item | Status |
|------|--------|
| SQLite online backup CLI | `scripts/backup_sqlite.py` |
| Guarded SQLite restore | `scripts/restore_sqlite.py` |
| Recovery verifier | `scripts/verify_recovery.py` |
| Postgres backup wrapper | `scripts/backup_postgres.py` (env-only secrets; `pg_restore --list`) |
| Retention dry-run | `scripts/backup_retention.py` |
| Operator runbook | `docs/BACKUP_AND_RECOVERY.md` |
| Tests | `tests/test_backup_*.py`, `test_restore_sqlite.py`, `test_verify_recovery.py` |
| CI synthetic SQLite drill | `.github/workflows/tests.yml` core-tests step |
| `docs/PRODUCTION.md` cross-link | **Pending** (coordinate release agent) |
| Postgres restore wrapper | `scripts/restore_postgres.py` |
| Destructive-delete tests | `tests/test_destructive_ops.py` |
| Full disposable Postgres restore CI | core-tests SQLite drill + postgres job dump/restore drill |
| Uploads archive | `scripts/backup_uploads.py` |
| Overlap lock | `scripts/backup_lock.py` (used by sqlite/uploads) |
| Security route matrix (Phase 1 seed) | `docs/SECURITY_ROUTE_MATRIX.md` (regenerate via `scripts/export_security_route_matrix.py`) |

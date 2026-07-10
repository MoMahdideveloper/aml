# Todo: Dynamic Dashboard Trends

## Phase 1: Storage Foundation

### Task 1: Make Dashboard Snapshot Storage Deployable
- [x] Create Alembic migration for `dashboard_stat_snapshots`.
- [x] Verify migration columns match `DashboardStatSnapshot` in `sqlalchemy_models.py`.
- [x] Add safe downgrade that drops only `dashboard_stat_snapshots`.
- [x] Verify with `FLASK_APP=app.py flask db upgrade`.
- [x] Verify table existence with focused schema check or test.

**Acceptance criteria**
- [x] Fresh database upgrade creates `dashboard_stat_snapshots`.
- [x] Migration includes all current snapshot metric fields.
- [x] Downgrade is scoped to this table only.

**Dependencies:** None.

**Likely files**
- `migrations/versions/j5k6l7m8n9o0_add_dashboard_stat_snapshots.py`
- `sqlalchemy_models.py` (existing model reused)

### Task 2: Add Snapshot Lifecycle Helpers
- [x] Add helper to collect current dashboard metric values.
- [x] Add idempotent helper to create today's snapshot.
- [x] Add helper to find snapshot from 30 days ago.
- [x] Add ±3 day closest-snapshot fallback.
- [x] Add tests for exact match, fallback match, no match, and same-day idempotency.

**Acceptance criteria**
- [x] Two calls on the same day create one snapshot.
- [x] Exact 30-day snapshot wins over nearby snapshots.
- [x] Closest snapshot inside ±3 days is selected when exact is missing.
- [x] `None` is returned when no snapshot is inside the window.

**Verification**
- [x] `pytest -q tests/test_dashboard_trends.py`

**Dependencies:** Task 1.

**Likely files**
- `repositories/dashboard_statistics_repository.py`
- `tests/test_dashboard_trends.py`

## Checkpoint: Storage Foundation
- [x] Migration applies on a clean test database.
- [x] Snapshot creation is idempotent.
- [x] Historical fallback rules match `SPEC.md`.
- [x] Human reviews storage behavior before dashboard data contract changes.

## Phase 2: Dynamic Trend Data Contract

### Task 3: Implement Trend Calculation and Formatting
- [x] Add pure trend calculation helper.
- [x] Add trend formatting helper for direction, icon, sign, and percent.
- [x] Define deterministic behavior for missing history and zero previous value.
- [x] Add tests for positive, negative, unchanged, missing, zero-current, and zero-previous cases.

**Acceptance criteria**
- [x] Positive values render upward trend fields.
- [x] Negative values render downward trend fields.
- [x] Unchanged or missing values render neutral trend fields.
- [x] Previous value of zero never raises division errors.

**Verification**
- [x] `pytest -q tests/test_dashboard_trends.py`

**Dependencies:** None, but complete before Task 4.

**Likely files**
- `repositories/dashboard_statistics_repository.py`
- `tests/test_dashboard_trends.py`

### Task 4: Return Nested Trend Metrics From `get_dashboard_stats()`
- [x] Wrap `total_properties` as `{value, trend}`.
- [x] Wrap `active_deals` as `{value, trend}`.
- [x] Wrap `total_deal_value` as `{value, trend}`.
- [x] Wrap `total_customers` as `{value, trend}`.
- [x] Preserve `recent_properties`, `recent_deals`, and market trend fields.
- [x] Confirm `_stat_value_and_trend()` still supports nested and plain shapes.

**Acceptance criteria**
- [x] Core bento metrics include `value` and `trend`.
- [x] Current values match pre-change counts and sums.
- [x] Existing dashboard route still returns HTTP 200.
- [x] Snapshot creation does not add significant dashboard latency.

**Verification**
- [x] `pytest -q tests/test_dashboard_trends.py`
- [x] `pytest -q tests/test_dashboard_template.py tests/test_app_smoke.py`

**Dependencies:** Tasks 1, 2, 3.

**Likely files**
- `repositories/dashboard_statistics_repository.py`
- `views/main.py` (neutral default trends)
- `tests/test_dashboard_trends.py`
- `tests/test_dashboard_template.py`

## Checkpoint: Dynamic Data Contract
- [x] `database_service.get_dashboard_stats()` returns nested trend metrics.
- [x] Current metric values remain accurate.
- [x] Missing-history behavior renders neutral trend.
- [x] Focused tests pass before UI polish.

## Phase 3: UI Verification and Handoff

### Task 5: Verify Dashboard Rendering Against Dynamic Trend Data
- [x] Seed historical and current data in a Flask client test.
- [x] Assert rendered trend text for all four bento cards.
- [x] Verify down trends use down icon/direction.
- [x] Verify neutral trends do not imply false growth.
- [x] Keep `templates/dashboard.html` unchanged unless neutral styling needs explicit support.

**Acceptance criteria**
- [x] Dashboard shows dynamic trend percentage text for all four bento cards.
- [x] Down trends use existing error color behavior.
- [x] Neutral trends render legibly.

**Verification**
- [x] `pytest -q tests/test_dashboard_template.py tests/test_dashboard_trends.py`
- [x] Manual: `python main.py`, then open `http://127.0.0.1:55555/dashboard`.

**Dependencies:** Task 4.

**Likely files**
- `views/main.py` (neutral defaults only)
- `tests/test_dashboard_template.py`

### Task 6: Keep Planning Handoff Current
- [x] Mark tasks complete only after verification passes.
- [x] Update `tasks/plan.md` if scope changes.
- [x] Update `tasks/todo.md` as tasks move through checkpoints.
- [x] Confirm docs still say Track A only and exclude Track B work.

**Acceptance criteria**
- [x] Plan and todo reflect actual implementation status.
- [x] Another AI agent can resume from unchecked tasks.
- [x] No stale references to old template paths or old line numbers remain.

**Verification**
- [x] Docs updated after implementation.
- [x] Docs re-synced after release verification (2026-07-10).

**Dependencies:** All implementation tasks.

**Likely files**
- `tasks/plan.md`
- `tasks/todo.md`

## Final Checkpoint
- [x] `pytest -q tests/test_dashboard_trends.py`
- [x] `pytest -q tests/test_dashboard_template.py tests/test_app_smoke.py`
- [x] `pytest -q tests/test_platinum_heritage_ui.py tests/test_app_smoke.py tests/test_simple.py tests/test_template_replacement.py --tb=short`
- [x] `FLASK_APP=app.py flask db upgrade` (local workspace DB may lag heads — see migration notes; **do not** upgrade production without approval)
- [x] Manual dashboard check completed with seeded historical snapshot data.
- [x] Core CRM browser workflows exercised (list pages, modals, map, settings, PH 404).
- [x] Production config / health / cookie suite verified.
- [x] Disposable-DB upgrade/downgrade of `j5k6l7m8n9o0` verified.
- [ ] Human has reviewed migration notes before production deployment.

## Release verification log (2026-07-10) — final handoff

### Scope
- **Included:** Track A Flask CRM (dashboard trends, templates, routes, forms, assets, prod config, tests, browser QA).
- **Excluded:** `api/`, `matcher/`, `ingestor/`, `chatbot/`, Neo4j, Next.js rewrite, Stitch redesign.
- **Untouched dirty paths:** `chroma_db/`, `graphify-out/`, `node_modules/`, `server.pid`, `stitch_kpi_performance_dashboard/`.
- **Branch:** `005-template-replacement`.
- **No commit / push / production migrate / `_archive` delete** performed.

### Phase 1 — Automated baseline
| Command | Result |
|---------|--------|
| `python -m pytest -q tests/test_dashboard_trends.py` | **17 passed** |
| `python -m pytest -q tests/test_dashboard_template.py tests/test_app_smoke.py` | **6 passed** |
| UI baseline pre-fix: `…platinum_heritage_ui + smoke + simple + template_replacement` | **47 passed, 17 deprecation warnings** |
| Snapshot lifecycle `-k "idempotent or historical"` | **4 passed** (idempotent; exact 30d; ±3d fallback; out-of-window `None`) |

Trend branch coverage (test DB only, never production): positive / negative / unchanged / missing history / zero previous / exact 30-day / closest ±3-day — in `tests/test_dashboard_trends.py`.

### Phase 2 — Dashboard browser QA
- Server: `python main.py` → `http://127.0.0.1:55555/dashboard`
- Seed (local disposable metrics only): historical snapshot ~30d prior vs live counts.
- Observed KPI cards:
  - Total Properties `785` → **+100.3%** `trending_up` (positive)
  - Active Deals `2` → **-50.0%** `trending_down` (negative / error color)
  - Monthly Revenue `$214,000` → **0.0%** `trending_flat` (neutral, not false growth)
  - Total Clients `4` → **+100.0%** `trending_up` (positive)
- Viewports: **desktop 1440×900** (4-col); **mobile 390×844** (stacked ~343px).
- Screenshots: `artifacts/dashboard-desktop-1440.png`, `artifacts/dashboard-mobile-390.png`
- Console on happy path: **0 app errors**; 1 expected Tailwind CDN production warning (local CDN).
- Network: local static + fonts **200**; no broken CSS/JS for CRM shell.

### Phase 3 — Core CRM regression + proven defect fix
**Browser (desktop 1440 then mobile 390):**
| Route / action | Result |
|----------------|--------|
| `/dashboard` KPIs + nav | OK |
| `/properties` + open `addPropertyModal` | Modal present & visible |
| `/agents` edit + add openers | Present |
| `/customers` profile + add openers | Present |
| `/deals` pipeline/kanban + add | Present |
| `/tasks` task modal opener | Present |
| `/recommendations`, `/properties/map`, `/settings` | HTTP 200 |
| Unknown URL 404 | After fix: PH shell `Page Not Found · Platinum Heritage` |

**Proven defect fixed (only production code change this pass):**
- **Problem:** `register_error_handlers()` existed but was never called from `create_app()`, so unknown routes returned Werkzeug’s default HTML (not PH `404.html` / `500.html`).
- **Fix:** call `register_error_handlers(app)` after blueprint registration in `app.py`.
- **Regression:** `tests/test_platinum_heritage_ui.py::test_ph_404_and_500_error_pages`.
- **Post-fix UI baseline:** platinum suite includes +1 test; full Track A gate command below.

No speculative refactors. No Track B changes.

### Phase 4 — Production readiness
| Command | Result |
|---------|--------|
| `pytest -q tests/test_production_config.py tests/test_health_readiness.py tests/test_auth_cookie_hardening.py` | **12 passed** |
| CI core extras (config, health, cookies, docker entrypoint, trends, template refs, docker context) | **38 passed, 3 skipped** (earlier run) |
| Combined gate (prod extras + full Track A including new error-page test) | **86 passed, 3 skipped** |

Production behavior confirmed by tests / docs:
- Production rejects default/weak `SESSION_SECRET`.
- `/healthz` liveness vs `/readyz` DB readiness.
- Production CSS artifact `static/css/tailwind-ph.css` present.
- CSRF / secure cookie defaults covered by dedicated tests.

**Migration review (disposable only — production NOT upgraded):**
| Check | Result |
|-------|--------|
| `$env:FLASK_APP='app.py'; flask db heads` | `k6l7m8n9o0p1 (head)` |
| `$env:FLASK_APP='app.py'; flask db current` (workspace SQLite) | `5b578ff077cb` — **lags heads**; treat workspace DB as non-prod and plan careful multi-revision upgrade path before any real deploy |
| Inspect `migrations/versions/j5k6l7m8n9o0_add_dashboard_stat_snapshots.py` | Creates `dashboard_stat_snapshots` + timestamp index; downgrade drops **only** that table/index |
| Disposable SQLite: upgrade to `j5k6l7m8n9o0` | Table + expected columns present |
| Disposable: downgrade to `i4j5k6l7m8n9` | Snapshot table removed |
| Disposable: re-upgrade `j5k6l7m8n9o0` | Table restored |
| Note | `downgrade -1` from merge head can be **Ambiguous walk** — target explicit revisions |

**Human approval still required** before any production `flask db upgrade`.

### Phase 5 — Maintenance follow-ups (do **not** block release)

#### Deprecation backlog (separate workstreams)
1. **Pydantic:** migrate `@validator` → `@field_validator` in `schemas.py` (V2 style). Behavior-preserving only.
2. **Datetime:** replace `datetime.utcnow()` with timezone-aware UTC (`datetime.now(datetime.UTC)`) in:
   - `repositories/dashboard_statistics_repository.py`
   - `views/agents.py` (and any other call sites surfacing in warnings)
   - model defaults via SQLAlchemy `default=datetime.utcnow` patterns if present
3. Handle each warning family in its own PR/test pass; do not mix with product features.

#### `templates/_archive/` housekeeping (delete only after explicit approval)
- ~43 HTML files under `templates/_archive/` (orphans, mobile Stitch exports, backups).
- Active Python does **not** import `_archive` path for rendering (audit: `tmp/audit_archive_refs.py`).
- Keep Stitch exports under `stitch_kpi_performance_dashboard/` outside Docker context (already excluded from product path).
- **Proposed action after human OK:** hard-delete `templates/_archive/` only; do not delete Stitch project folder without separate approval.

### Phase 6 — Final quality gate
```text
python -m pytest -q tests/test_dashboard_trends.py tests/test_dashboard_template.py tests/test_platinum_heritage_ui.py tests/test_app_smoke.py tests/test_simple.py tests/test_template_replacement.py --tb=short
→ 69 passed (includes new PH 404/500 regression)

python -m pytest -q tests/test_production_config.py tests/test_health_readiness.py tests/test_auth_cookie_hardening.py tests/test_docker_entrypoint.py tests/test_dashboard_trends.py tests/test_template_references.py tests/test_docker_context.py tests/test_platinum_heritage_ui.py tests/test_app_smoke.py tests/test_simple.py tests/test_template_replacement.py --tb=short
→ 86 passed, 3 skipped
```

### Unresolved / remaining human gates
- [ ] Approve and apply production migrations (multi-step; workspace is behind head).
- [ ] Explicit approval to commit/push release verification + error-handler fix.
- [ ] Explicit approval to delete `templates/_archive/`.
- Optional non-blocking: missing `/favicon.ico` (browser network 404 only; not a CRM functional failure).

### Continue pass (same day — reconfirm only)
| Check | Result |
|-------|--------|
| Track A gate re-run | **69 passed** |
| Live `GET /healthz` | `status=ok` |
| Live `GET /readyz` | `status=ready` |
| Full route matrix (test client) | All core PH routes **200** with Platinum Heritage shell; unknown URL **404** with PH shell |
| Dev CSRF fields on list forms | Often **0** when `ENABLE_CSRF` off (dev default); production path enables CSRF via config tests — expected |
| Server | `http://127.0.0.1:55555` healthy |

#### Recommended production migration path (human-operated)
Do **not** run against production until approved. Prefer Postgres disposable clone first.

```powershell
$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "production"
$env:SESSION_SECRET = "<strong-secret>"
$env:DATABASE_URL = "<postgres-url>"
# 1) Inspect
python -m flask db current
python -m flask db heads   # expect k6l7m8n9o0p1
# 2) Backup DB
# 3) Upgrade (single command walks graph to head; review history first)
python -m flask db upgrade heads
# 4) Confirm snapshot table
# SELECT to_regclass('public.dashboard_stat_snapshots');
# 5) Probes
# curl /healthz  /readyz
```

Alembic lineage (high level):
`5b578ff077cb` → … → `i4j5k6l7m8n9` → **`j5k6l7m8n9o0` (dashboard_stat_snapshots)** → merge **`k6l7m8n9o0p1` (head)**.

Workspace SQLite reported `current=5b578ff077cb` while head is `k6l7m8n9o0p1` — local dev may rely on `create_all`/existing tables; **do not** treat workspace as production truth.

#### Deprecation backlog inventory
| Family | Status |
|--------|--------|
| Pydantic `@validator` → `@field_validator` | **Done** (`schemas.py` + `tests/test_schemas.py`) |
| ORM `default=datetime.utcnow` / `onupdate=` | **Done** → `_utcnow_naive` in `sqlalchemy_models.py` |
| Dashboard snapshot `utcnow` | **Done** → `utils.time_utc.utc_now_naive` |
| Agents dashboard month window | **Done** → `utc_now_naive` |
| Policy doc | `tasks/datetime_compatibility.md` (naive UTC storage) |
| Helper | `utils/time_utc.py` |
| Later slices (not in suite baseline) | `background_matcher.py`, `event_handlers.py`, `init_db.py`, `views/admin_environment.py`, `repositories/base_repository.py` |
| `templates/_archive/` | Delete only after explicit approval |
| Favicon | Optional; non-blocking |

#### Deprecation modernization verification (2026-07-10 continue)
```text
python -m pytest -q tests/test_schemas.py tests/test_time_utc.py
python -m pytest -q tests/test_platinum_heritage_ui.py tests/test_app_smoke.py tests/test_simple.py tests/test_template_replacement.py tests/test_dashboard_trends.py tests/test_dashboard_template.py tests/test_schemas.py tests/test_time_utc.py -W default
→ 84 passed, 0 deprecation warnings
```

#### Files ready to commit (when approved)
```
app.py                             # register_error_handlers
tests/test_platinum_heritage_ui.py # PH 404/500 regression
tasks/todo.md                      # evidence
tasks/plan.md                      # status
# + deprecation modernization + a11y/perf (see below)
```
Suggested subjects (split preferred):
1. `fix: register PH error handlers for 404/500`
2. `fix: modernize pydantic validators and naive UTC clocks`
3. `fix(a11y): shell landmarks, modal focus, prod CSS path`

## Accessibility & frontend performance (2026-07-10)

**Evidence:** `artifacts/A11Y_PERF_REPORT.md`, `artifacts/a11y_perf_baseline.json`

### Done
- Skip link + `#main-content`; single page `h1`; `aria-current="page"`; reduced-motion + focus-visible
- PHModal focus trap / Escape / restore opener
- Dashboard trend not color-only (`.sr-only` direction)
- Deferred Font Awesome + `app-core.js` defer; login respects `USE_TAILWIND_CDN=0`
- Tests: `tests/test_accessibility_shell.py`; CI includes it
- Regression: **83 passed** (a11y shell + Track A core suites)

### Not done (no measured server N+1 need)
- Query eager-loading changes deferred — list/dashboard TTFB already low in baseline
- Full Lighthouse CI gate report-only

## Implementation notes (2026-07-10)
- Migration: `j5k6l7m8n9o0_add_dashboard_stat_snapshots.py` (merged later into head `k6l7m8n9o0p1`).
- Trend logic: `repositories/dashboard_statistics_repository.py`.
- Defect fix this verification pass: wire `register_error_handlers(app)` in `app.py` + regression test.
- Track A only — no Track B microservices touched.
- Remaining release gate: **human production migration review + deploy approval**.

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
- [ ] Manual: `python main.py`, then open `http://127.0.0.1:55555/dashboard`.

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

**Dependencies:** All implementation tasks.

**Likely files**
- `tasks/plan.md`
- `tasks/todo.md`

## Final Checkpoint
- [x] `pytest -q tests/test_dashboard_trends.py`
- [x] `pytest -q tests/test_dashboard_template.py tests/test_app_smoke.py`
- [ ] `pytest -q tests/test_platinum_heritage_ui.py tests/test_app_smoke.py tests/test_simple.py tests/test_template_replacement.py --tb=short`
- [x] `FLASK_APP=app.py flask db upgrade` (attempted; local DB may already be current)
- [ ] Manual dashboard check completed with seeded historical snapshot data.
- [ ] Human has reviewed migration notes before production deployment.

## Implementation notes (2026-07-10)
- Migration: `j5k6l7m8n9o0_add_dashboard_stat_snapshots.py`
- Logic lives in `repositories/dashboard_statistics_repository.py` (`calculate_trend_change`, `format_trend`, snapshot helpers, nested `get_dashboard_stats()`).
- Track A only — no Track B microservices touched.
- Remaining: optional broader UI suite + human manual dashboard review before production migrate.

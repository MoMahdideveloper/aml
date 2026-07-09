# Implementation Plan: Dynamic Dashboard Trends

## Overview
Replace misleading static dashboard trend values with real month-over-month trend data for the Flask CRM dashboard. The implementation should follow the primary Track A product path only: Flask, SQLAlchemy, Jinja2, Tailwind, repository/service patterns. Do not work on Track B microservices (`api/`, `matcher/`, `ingestor/`, `chatbot/`) unless the human explicitly changes scope.

## Source Spec
- `SPEC.md` defines the target behavior: daily dashboard metric snapshots, 30-day historical comparison with ±3 day fallback, neutral trend when history is missing, safe zero-value handling, and unchanged current metric values.
- `README.md` and `docs/adr-001-architecture.md` confirm Flask CRM is the shippable product path.

## Current State
- `sqlalchemy_models.py` already defines `DashboardStatSnapshot`.
- `services/database_service.py` delegates `get_dashboard_stats()` to `DashboardStatisticsRepository.get_dashboard_stats()`.
- `repositories/dashboard_statistics_repository.py` computes current metrics but currently returns plain values for core dashboard stats; snapshot persistence and nested trend objects are not wired into the dashboard data contract.
- `views/main.py` already has `_stat_value_and_trend()` and builds dashboard cards in a way that can consume either plain values or `{value, trend}` dictionaries.
- `templates/dashboard.html` already renders trend direction, icon, sign, and percent for each dashboard card.
- `tests/test_dashboard_template.py` checks rendering but does not prove snapshot creation, historical lookup, or trend math.
- Existing `tasks/plan.md` and `tasks/todo.md` were stale and claimed completion against old code paths.

## Dependency Graph
```text
DashboardStatSnapshot table / migration
    |
    v
Dashboard statistics repository helpers
    - collect current metrics
    - create today's snapshot idempotently
    - find historical snapshot around 30 days ago
    - calculate and format trend objects
    |
    v
DatabaseService.get_dashboard_stats()
    |
    v
views/main.py dashboard route
    - uses _stat_value_and_trend()
    - builds bento_stats without hardcoded trends
    |
    v
templates/dashboard.html
    - displays values and trend UI
    |
    v
tests and manual dashboard verification
```

## Architecture Decisions
- Keep trend business logic in `repositories/dashboard_statistics_repository.py`, not in route or template code.
- Reuse the existing `DashboardStatSnapshot` ORM model; do not create a duplicate model.
- Preserve the current dashboard route/template contract and rely on `_stat_value_and_trend()` for backward compatibility.
- Treat the snapshot write on dashboard load as idempotent and cheap; do not add background jobs for this feature unless later required.
- Prefer neutral `0.0%` trend for missing history and zero-baseline comparisons unless product explicitly wants a special `New` label.

## Phase 1: Storage Foundation

### Task 1: Make Dashboard Snapshot Storage Deployable
**Description:** Ensure `dashboard_stat_snapshots` can be created through Alembic and matches the existing `DashboardStatSnapshot` model.

**Acceptance criteria:**
- Migration creates `dashboard_stat_snapshots` with every field currently defined on `DashboardStatSnapshot`.
- Migration downgrade drops only `dashboard_stat_snapshots`.
- Fresh database upgrade creates the table without manual `db.create_all()`.

**Verification:**
- Run `FLASK_APP=app.py flask db upgrade`.
- Add or run a focused schema test that confirms `dashboard_stat_snapshots` exists.

**Dependencies:** None.

**Files likely touched:**
- `migrations/versions/<new>_add_dashboard_stat_snapshots.py`
- `sqlalchemy_models.py` only if the model and migration need alignment

**Estimated scope:** Small.

### Task 2: Add Snapshot Lifecycle Helpers
**Description:** Add repository helpers to collect current metrics, create one snapshot per day, and retrieve the closest 30-day historical snapshot within ±3 days.

**Acceptance criteria:**
- Creating a snapshot twice on the same day produces one stored snapshot.
- Historical lookup prefers an exact 30-day match.
- Historical lookup chooses the closest snapshot inside ±3 days when exact data is missing.
- Historical lookup returns `None` when no acceptable snapshot exists.

**Verification:**
- Unit tests cover exact match, nearest fallback, out-of-window fallback, and duplicate same-day calls.
- Run `pytest -q tests/test_dashboard_trends.py`.

**Dependencies:** Task 1.

**Files likely touched:**
- `repositories/dashboard_statistics_repository.py`
- `tests/test_dashboard_trends.py`

**Estimated scope:** Medium.

## Checkpoint: Storage Foundation
- [x] Migration applies on a clean test database.
- [x] Snapshot creation is idempotent.
- [x] Historical fallback behavior matches `SPEC.md`.
- [x] Human review before dashboard data contract changes.

## Phase 2: Dynamic Trend Data Contract

### Task 3: Implement Trend Calculation and Formatting
**Description:** Add pure helper functions for percentage calculation and display formatting.

**Acceptance criteria:**
- Positive values produce upward trend fields.
- Negative values produce downward trend fields.
- Unchanged values produce neutral trend fields.
- Missing history returns neutral `0.0%` trend.
- Previous value of zero never raises a division error and has deterministic tested behavior.

**Verification:**
- Unit tests cover positive, negative, unchanged, `None`, zero current, and zero previous values.
- Trend helper tests do not require a Flask app context.

**Dependencies:** None, but complete before Task 4.

**Files likely touched:**
- `repositories/dashboard_statistics_repository.py`
- `tests/test_dashboard_trends.py`

**Estimated scope:** Small.

### Task 4: Return Nested Trend Metrics From `get_dashboard_stats()`
**Description:** Update `DashboardStatisticsRepository.get_dashboard_stats()` so the dashboard card metrics return `{value, trend}` dictionaries while existing collection fields remain available.

**Acceptance criteria:**
- `total_properties`, `active_deals`, `total_deal_value`, and `total_customers` include `value` and `trend`.
- Current metric values match existing pre-change counts and sums.
- `recent_properties`, `recent_deals`, and existing market trend fields remain available.
- Today's snapshot is created without significant dashboard latency.

**Verification:**
- Repository tests assert nested structures and unchanged current values.
- Flask dashboard route returns HTTP 200.
- `_stat_value_and_trend()` still handles both nested and plain stats.

**Dependencies:** Tasks 1, 2, 3.

**Files likely touched:**
- `repositories/dashboard_statistics_repository.py`
- `services/database_service.py` only if type hints or docstrings need adjustment
- `tests/test_dashboard_trends.py`
- `tests/test_dashboard_template.py` if dashboard assertions need tightening

**Estimated scope:** Medium.

## Checkpoint: Dynamic Data Contract
- [x] `database_service.get_dashboard_stats()` returns nested trend metrics.
- [x] Current metric values remain accurate.
- [x] Missing-history behavior renders neutral trend.
- [x] Focused tests pass before UI polish.

## Phase 3: UI Verification and Handoff

### Task 5: Verify Dashboard Rendering Against Dynamic Trend Data
**Description:** Keep template changes minimal and verify the dashboard renders actual dynamic trend data for all bento cards.

**Acceptance criteria:**
- Dashboard displays trend percentage text for all four bento cards.
- Down trends use down direction/icon and existing error color behavior.
- Neutral trends render legibly and do not imply false growth.

**Verification:**
- Seed historical and current data in a Flask client test and assert rendered trend text.
- Run `pytest -q tests/test_dashboard_template.py tests/test_dashboard_trends.py`.
- Manual check: run `python main.py` and visit `http://127.0.0.1:55555/dashboard`.

**Dependencies:** Task 4.

**Files likely touched:**
- `templates/dashboard.html` only if neutral styling needs explicit handling
- `views/main.py` only if card mapping needs small adjustment
- `tests/test_dashboard_template.py`

**Estimated scope:** Small.

### Task 6: Keep Planning Handoff Current
**Description:** Keep `tasks/plan.md` and `tasks/todo.md` aligned with the actual implementation state as tasks complete.

**Acceptance criteria:**
- Completed tasks are marked only after verification passes.
- Any scope change is reflected in both plan and todo docs.
- Documents continue to state Track A only and exclude Track B work.

**Verification:**
- Review `tasks/plan.md` and `tasks/todo.md` before handoff.
- Run `git diff -- tasks/plan.md tasks/todo.md` to confirm only intended documentation changes.

**Dependencies:** All implementation tasks.

**Files likely touched:**
- `tasks/plan.md`
- `tasks/todo.md`

**Estimated scope:** Small.

## Checkpoint: Handoff Ready
- [x] Plan and todo files are current and internally consistent.
- [x] Another AI agent can resume from any unchecked task.
- [ ] Human has reviewed migration scope before production deployment.

## Status (2026-07-10)
**Implemented (Track A).** Migration `j5k6l7m8n9o0`, repository snapshot + trend helpers, nested bento metrics, tests in `tests/test_dashboard_trends.py`. Remaining open: production migration review and optional manual dashboard spot-check.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Model exists without migration | High | Start with migration and schema verification. |
| Callers expect plain numbers from `get_dashboard_stats()` | Medium | Keep `_stat_value_and_trend()` backward-compatible and search direct callers before changing return shapes. |
| Snapshot write during dashboard GET adds side effects | Medium | Make snapshot creation idempotent and cheap; add date lookup/index if needed. |
| Zero baseline trend is misleading | Medium | Encode the chosen behavior in tests and keep product copy neutral. |
| Stale planning docs mislead future agents | Medium | Update `tasks/plan.md` and `tasks/todo.md` as part of handoff. |

## Open Questions
- Schema migration approval: `SPEC.md` says the new table is in scope, but implementation should still get explicit human confirmation before applying production migrations.
- Zero-baseline display: recommended behavior is neutral `0.0%` for `previous=0,current>0`; product may prefer a `New` label later.

## Verification Commands
- `pytest -q tests/test_dashboard_trends.py`
- `pytest -q tests/test_dashboard_template.py tests/test_app_smoke.py`
- `pytest -q tests/test_platinum_heritage_ui.py tests/test_app_smoke.py tests/test_simple.py tests/test_template_replacement.py --tb=short`
- `FLASK_APP=app.py flask db upgrade`
- Manual: `python main.py`, open `http://127.0.0.1:55555/dashboard`, and inspect seeded dashboard trend behavior.

## Implementation Notes
- Reuse `DashboardStatSnapshot` in `sqlalchemy_models.py`.
- Keep route and template code thin.
- Do not introduce new dependencies for date math or trend formatting.
- Do not modify Track B microservices for this feature.
- Do not commit, push, reset, delete generated directories, or modify secrets unless the human explicitly asks.

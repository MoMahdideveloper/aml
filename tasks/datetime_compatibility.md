# Datetime compatibility policy (Track A)

**Date:** 2026-07-10  
**Scope:** Runtime deprecation modernization — no behavior change.

## Decision

**Database `DateTime` columns store naive UTC** (no `tzinfo`).

Evidence:
- Columns use SQLAlchemy `DateTime` without `timezone=True`.
- Migrations create plain `DateTime` / TIMESTAMP without timezone constraints.
- Application code compares timestamps with naive `datetime` values.
- Serialization uses `.isoformat()` on naive values (no explicit `Z` / offset contract).

## Convention

| Layer | Convention |
|-------|------------|
| Source of truth for “now” | `datetime.now(UTC)` (aware) |
| Persist / compare with DB | `datetime.now(UTC).replace(tzinfo=None)` → **naive UTC** |
| Shared helper | `utils.time_utc.utc_now_naive()` (and `utc_now()` if aware is needed) |
| Forbidden | Mixing aware DB values with naive column comparisons without an explicit convert |

## Why not migrate columns to timezone-aware?

Changing column types / stored formats is a schema and data migration. Out of scope for warning cleanup. Keep stored format identical; only change how “now” is obtained.

## Out of scope (later slices)

- `background_matcher.py`, `event_handlers.py`, `init_db.py`, admin env views: same helper when those modules are touched.
- Postgres `TIMESTAMPTZ` migration: separate project if product requires it.

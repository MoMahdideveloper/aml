# Specification: Dynamic Dashboard Trends

## Objective
Replace hardcoded trend values in the dashboard with dynamically calculated month-over-month changes to provide accurate performance metrics for real estate agents and administrators.

## Core Features
1. **Daily Snapshot Storage**: Persist key dashboard metrics once per day to enable historical comparisons.
2. **Trend Calculation**: Compute month-over-month percentage changes for each metric.
3. **Dynamic Trend Display**: Replace static trend values (+12.5%, +8.2%, etc.) with calculated values showing direction, icon, sign, and percentage.
4. **Edge Case Handling**: Gracefully manage scenarios with insufficient historical data or zero values.

## Acceptance Criteria
- [ ] Dashboard displays trend data reflecting actual changes from approximately 30 days prior.
- [ ] When 30-day-old data unavailable, uses closest available snapshot within ±3 days.
- [ ] When no historical data exists, displays neutral trend (0% change).
- [ ] Handles division by zero when previous period value is zero.
- [ ] Existing dashboard metric values (current values) remain unchanged and accurate.
- [ ] Solution does not degrade application performance significantly.

## Technical Implementation
### Commands (Key Operations)
- `create_daily_snapshot()`: Stores current metrics if no snapshot exists for today.
- `get_historical_snapshot(days_ago=30)`: Retrieves snapshot from specified days ago or closest alternative.
- `calculate_trend(current, previous)`: Computes percentage change and formats trend object.
- `format_trend(change)`: Converts decimal change to direction, icon, sign, and percentage string.

### Project Structure Changes
- **New Model**: `database_service.py` → Add `DashboardStatSnapshot` SQLAlchemy model.
- **Modified Service**: `database_service.py` → Update `get_dashboard_stats()` to:
  1. Create today's snapshot if missing
  2. Retrieve 30-day-old snapshot
  3. Calculate trends for each metric
  4. Return nested structure with values and trend objects
- **Updated View**: `views/main.py` → Dashboard route to handle new nested data structure.
- **Updated Template**: `templates/dashboard_overview.html` → Use dynamic trend data instead of hardcoded values.

### Code Style
- Follow existing PEP8 compliance in Python files.
- Maintain current Jinja2 template syntax and Tailwind CSS usage.
- Preserve existing naming conventions (snake_case for variables/functions, CamelCase for classes).
- Keep SQLAlchemy model definitions consistent with current `sqlalchemy_models.py` style.
- Add docstrings to new/modified functions and classes.

### Testing Strategy
1. **Unit Tests**:
   - Test `calculate_trend()` with various inputs (positive, negative, zero, None).
   - Test snapshot creation logic (idempotent daily creation).
   - Test historical snapshot retrieval (exact match, fallback to nearest).
   - Test trend formatting for edge cases (zero previous value, negative change).
2. **Integration Tests**:
   - Verify dashboard route returns correct template context with trend data.
   - Confirm template renders trend values correctly (direction, icon, sign, percent).
   - Ensure snapshot table is created and populated correctly.
3. **Manual Verification**:
   - Deploy test data with known data from 30 days ago.
   - Check behavior when no historical data exists.
   - Validate dashboard still shows correct current values.
   - Test responsive design across device sizes.

### Boundaries (from CLAUDE.md and Project Context)
**Always Do**:
- Use `byterover-retrive-knowledge` before starting implementation tasks.
- Use `byterover-store-knowledge` after completing significant implementation steps.
- Follow existing Flask blueprint and service patterns.
- Maintain backward compatibility where possible.
- Write defensive code with proper error handling.

**Ask First Before**:
- Modifying database schema (though adding new table is within scope).
- Changing the return signature of `get_dashboard_stats()` (requires view/template updates).
- Altering template structure beyond replacing hardcoded trend values.
- Adding new dependencies (aim to use existing Flask/SQLAlchemy stack).

**Never Do**:
- Break existing authentication or authorization flows.
- Compromise data integrity or security.
- Remove or break existing dashboard metric value displays.
- Ignore error conditions in snapshot creation/trend calculation.
- Commit sensitive data or credentials to repository.
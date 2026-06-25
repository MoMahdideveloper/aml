# Tasks: Replace Flask Templates with Stitch KPI Dashboard Designs

**Input**: Design documents from `/specs/005-template-replacement/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/, quickstart.md

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
   → quickstart.md: Extract validation tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `src/`, `tests/` at repository root
- **Web app**: `backend/src/`, `frontend/src/`
- **Mobile**: `api/src/`, `ios/src/` or `android/src/`
- Paths shown below assume single project - adjust based on plan.md structure

## Phase 3.1: Setup
- [ ] T001 Verify project structure matches web application option from plan.md
- [ ] T002 [P] Check that Stitch KPI dashboard designs are available in stitch_kpi_performance_dashboard/ directory
- [ ] T003 [P] Verify no conflicting files in templates/ directory

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Create test template for verifying template replacement (tests/test_template_replacement.py)
- [ ] T005 [P] Create test for dynamic data injection in dashboard template (tests/test_dashboard_template.py)
- [ ] T006 [P] Create test for dynamic data injection in properties template (tests/test_properties_template.py)
- [ ] T007 [P] Create test for dynamic data injection in customers template (tests/test_customers_template.py)
- [ ] T008 [P] Create test for dynamic data injection in deals template (tests/test_deals_template.py)
- [ ] T009 [P] Create test for dynamic data injection in tasks template (tests/test_tasks_template.py)
- [ ] T010 [P] Create test for dynamic data injection in agents template (tests/test_agents_template.py)
- [ ] T011 [P] Create test for dynamic data injection in recommendations template (tests/test_recommendations_template.py)
- [ ] T012 [P] Create test for form submissions with new templates (tests/test_forms_templates.py)
- [ ] T013 [P] Create test for AJAX requests with new templates (tests/test_ajax_templates.py)
- [ ] T014 [P] Create test for responsive behavior (tests/test_responsive_templates.py)
- [ ] T015 [P] Create test for existing functionality preservation (tests/test_regression_templates.py)

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T016 Analyze Stitch KPI dashboard designs to identify equivalent templates for each Flask route
- [ ] T017 Create base template (templates/base.html) adapted from Stitch design with Jinja2 blocks
- [ ] T018 Convert Stitch dashboard_overview/index.html to Jinja2 template for dashboard (templates/dashboard.html)
- [ ] T019 Convert Stitch properties/index.html to Jinja2 template for properties (templates/properties.html)
- [ ] T020 Convert Stitch customers/index.html to Jinja2 template for customers (templates/customers.html)
- [ ] T021 Convert Stitch deals/index.html to Jinja2 template for deals (templates/deals.html)
- [ ] T022 Convert Stitch tasks/index.html to Jinja2 template for tasks (templates/tasks.html)
- [ ] T023 Convert Stitch agents/index.html to Jinja2 template for agents (templates/agents.html)
- [ ] T024 Convert Stitch recommendations/index.html to Jinja2 template for recommendations (templates/recommendations.html)
- [ ] T025 [P] Copy and adapt Stitch CSS files to static/css/stitch/
- [ ] T026 [P] Copy and adapt Stitch JavaScript files to static/js/stitch/
- [ ] T027 [P] Copy and adapt Stitch image assets to static/img/stitch/
- [ ] T028 Update base.html to include Stitch CSS and JS via url_for()
- [ ] T029 Ensure all templates extend base.html and use appropriate blocks
- [ ] T030 Verify CSRF tokens are included in forms
- [ ] T031 Verify form field names and IDs match Flask-WTF expectations
- [ ] T032 Test that static assets are correctly served in development

## Phase 3.4: Integration
- [ ] T033 Integrate templates with Flask application by ensuring routes point to correct templates
- [ ] T034 Test that all existing routes render with new templates
- [ ] T035 Verify dynamic data is correctly injected in all templates
- [ ] T036 Test form submissions work with new templates
- [ ] T037 Test AJAX requests work with new templates
- [ ] T038 Check that template inheritance works correctly
- [ ] T039 Validate that no template syntax errors exist
- [ ] T040 Ensure static assets are correctly linked in all templates

## Phase 3.5: Polish
- [ ] T041 [P] Run performance tests to ensure page load times do not increase by more than 20%
- [ ] T042 [P] Test responsive behavior on various device sizes
- [ ] T043 [P] Validate accessibility (WCAG 2.1 AA) where applicable
- [ ] T044 [P] Check for any JavaScript console errors
- [ ] T045 [P] Verify no broken image or resource links
- [ ] T046 [P] Conduct manual exploratory testing of all features
- [ ] T047 [P] Update documentation if needed
- [ ] T048 [P] Run existing test suite to ensure no regressions
- [ ] T049 [P] Create backup of original templates (optional)
- [ ] T050 [P] Clean up any temporary files
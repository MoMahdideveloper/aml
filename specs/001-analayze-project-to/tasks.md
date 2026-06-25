# Tasks: Project Analysis & Future Suggestions

**Input**: Design documents from `/specs/001-analayze-project-to/`
**Prerequisites**: plan.md (✓), research.md (✓), data-model.md (✓), contracts/ (✓), quickstart.md (✓)

## Execution Flow (main)
```
1. Load plan.md from feature directory ✓
   → Tech stack: Python 3.11+, Flask 3.0+, SQLAlchemy 2.0+
   → Structure: Web application (extends existing Flask CRM)
2. Load design documents ✓:
   → data-model.md: 5 entities → 5 model tasks
   → contracts/: 1 file → 7 contract test tasks  
   → quickstart.md: 3 integration scenarios → 3 integration test tasks
3. Generate tasks by category ✓
4. Apply task rules: [P] for different files, TDD order ✓
5. Number tasks sequentially (T001-T030) ✓
6. Generate dependency graph ✓
7. Validate completeness ✓
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- File paths relative to repository root

## Phase 3.1: Setup
- [ ] **T001** Create analysis service module structure in analysis_service/ directory
- [ ] **T002** Add analysis dependencies to requirements.txt (radon, bandit, flake8, mypy)  
- [ ] **T003** [P] Configure analysis tools configuration files (.flake8, mypy.ini, bandit.yaml)

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (API Endpoints)
- [ ] **T004** [P] Contract test POST /api/analysis/trigger in tests/contract/test_analysis_trigger.py
- [ ] **T005** [P] Contract test GET /api/analysis/reports in tests/contract/test_analysis_reports_list.py
- [ ] **T006** [P] Contract test GET /api/analysis/reports/{id} in tests/contract/test_analysis_reports_detail.py
- [ ] **T007** [P] Contract test GET /api/analysis/reports/{id}/status in tests/contract/test_analysis_status.py
- [ ] **T008** [P] Contract test GET /api/analysis/suggestions in tests/contract/test_analysis_suggestions.py
- [ ] **T009** [P] Contract test PUT /api/analysis/suggestions/{id} in tests/contract/test_suggestions_update.py
- [ ] **T010** [P] Contract test GET /api/analysis/export/{id} in tests/contract/test_analysis_export.py

### Integration Tests (User Scenarios)
- [ ] **T011** [P] Integration test complete analysis workflow in tests/integration/test_complete_analysis_workflow.py
- [ ] **T012** [P] Integration test incremental analysis in tests/integration/test_incremental_analysis.py  
- [ ] **T013** [P] Integration test suggestion filtering in tests/integration/test_suggestion_filtering.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Database Models
- [ ] **T014** [P] AnalysisReport model in analysis_service/models/analysis_report.py
- [ ] **T015** [P] SuggestionItem model in analysis_service/models/suggestion_item.py
- [ ] **T016** [P] AnalysisDimension model in analysis_service/models/analysis_dimension.py
- [ ] **T017** [P] MetricSnapshot model in analysis_service/models/metric_snapshot.py
- [ ] **T018** [P] SuggestionTag model in analysis_service/models/suggestion_tag.py

### Service Layer
- [ ] **T019** CodeAnalysisService for codebase evaluation in analysis_service/services/code_analysis_service.py
- [ ] **T020** SuggestionEngine for generating recommendations in analysis_service/services/suggestion_engine.py
- [ ] **T021** ExportService for report generation in analysis_service/services/export_service.py

### API Endpoints (Blueprint)
- [ ] **T022** Analysis blueprint setup and registration in views/analysis.py
- [ ] **T023** POST /api/analysis/trigger endpoint implementation in views/analysis.py
- [ ] **T024** GET /api/analysis/reports and GET /api/analysis/reports/{id} endpoints in views/analysis.py
- [ ] **T025** GET /api/analysis/reports/{id}/status endpoint in views/analysis.py
- [ ] **T026** GET /api/analysis/suggestions endpoint with filtering in views/analysis.py
- [ ] **T027** PUT /api/analysis/suggestions/{id} endpoint in views/analysis.py
- [ ] **T028** GET /api/analysis/export/{id} endpoint in views/analysis.py

## Phase 3.4: Integration
- [ ] **T029** Database migration for analysis tables in migrations/versions/
- [ ] **T030** Update app.py to register analysis blueprint
- [ ] **T031** Background task integration for long-running analysis using APScheduler
- [ ] **T032** Error handling and logging for analysis operations

## Phase 3.5: Polish
- [ ] **T033** [P] Unit tests for CodeAnalysisService in tests/unit/test_code_analysis_service.py
- [ ] **T034** [P] Unit tests for SuggestionEngine in tests/unit/test_suggestion_engine.py
- [ ] **T035** [P] Unit tests for ExportService in tests/unit/test_export_service.py
- [ ] **T036** Performance optimization for analysis completion <30 seconds
- [ ] **T037** [P] Update CLAUDE.md documentation (already completed)
- [ ] **T038** Web dashboard templates in templates/analysis/ directory
- [ ] **T039** Frontend JavaScript for analysis dashboard in static/js/analysis.js
- [ ] **T040** Run quickstart.md manual validation scenarios

## Dependencies

### Critical Path (TDD)
1. **Setup** (T001-T003) → **Tests** (T004-T013) → **Implementation** (T014-T032) → **Polish** (T033-T040)
2. **Tests MUST fail before implementation begins**

### Model Dependencies
- T014 (AnalysisReport) blocks T015-T018 (related models need base entity)
- T014-T018 block T019-T021 (services need models)

### Service Dependencies  
- T019-T021 block T023-T028 (endpoints need services)
- T022 (blueprint setup) blocks T023-T028 (endpoints need blueprint)

### Integration Dependencies
- T029 (migration) before T030 (app registration)
- T030 before T031 (background tasks need registered blueprint)

## Parallel Execution Examples

### Phase 3.2: All Contract Tests (T004-T010)
```bash
# Launch T004-T010 together - different files, no dependencies:
Task: "Contract test POST /api/analysis/trigger in tests/contract/test_analysis_trigger.py"
Task: "Contract test GET /api/analysis/reports in tests/contract/test_analysis_reports_list.py" 
Task: "Contract test GET /api/analysis/reports/{id} in tests/contract/test_analysis_reports_detail.py"
Task: "Contract test GET /api/analysis/reports/{id}/status in tests/contract/test_analysis_status.py"
Task: "Contract test GET /api/analysis/suggestions in tests/contract/test_analysis_suggestions.py"
Task: "Contract test PUT /api/analysis/suggestions/{id} in tests/contract/test_suggestions_update.py"
Task: "Contract test GET /api/analysis/export/{id} in tests/contract/test_analysis_export.py"
```

### Phase 3.2: All Integration Tests (T011-T013)
```bash
# Launch T011-T013 together - different files, independent scenarios:
Task: "Integration test complete analysis workflow in tests/integration/test_complete_analysis_workflow.py"
Task: "Integration test incremental analysis in tests/integration/test_incremental_analysis.py"
Task: "Integration test suggestion filtering in tests/integration/test_suggestion_filtering.py"
```

### Phase 3.3: All Model Creation (T014-T018)
```bash
# After T014 completes, launch T015-T018 together:
Task: "SuggestionItem model in analysis_service/models/suggestion_item.py"
Task: "AnalysisDimension model in analysis_service/models/analysis_dimension.py" 
Task: "MetricSnapshot model in analysis_service/models/metric_snapshot.py"
Task: "SuggestionTag model in analysis_service/models/suggestion_tag.py"
```

### Phase 3.5: Unit Test Suite (T033-T035)
```bash
# Launch T033-T035 together - different test files:
Task: "Unit tests for CodeAnalysisService in tests/unit/test_code_analysis_service.py"
Task: "Unit tests for SuggestionEngine in tests/unit/test_suggestion_engine.py"
Task: "Unit tests for ExportService in tests/unit/test_export_service.py"
```

## Task Validation Checklist
✅ **All contracts have corresponding tests**: 7 endpoints → 7 contract tests (T004-T010)
✅ **All entities have model tasks**: 5 entities → 5 model tasks (T014-T018)  
✅ **All tests come before implementation**: Phase 3.2 (T004-T013) before Phase 3.3 (T014-T032)
✅ **Parallel tasks truly independent**: [P] tasks use different files with no shared dependencies
✅ **Each task specifies exact file path**: All tasks include specific file locations
✅ **No [P] task conflicts**: No two [P] tasks modify the same file

## Notes
- Total tasks: 40 (T001-T040)
- [P] tasks: 18 (can run in parallel groups)
- Sequential tasks: 22 (have dependencies)
- Estimated completion: 3-4 development days with parallel execution
- Critical TDD requirement: Tests T004-T013 must fail before implementing T014-T032
- Web application structure: Extends existing Flask CRM with new analysis blueprint
- Performance target: Analysis completes in <30 seconds (validated in T036)
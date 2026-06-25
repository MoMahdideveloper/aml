# Tasks: UI Review Feature in n8n

**Input**: Design documents from `/specs/004-review-all-specified/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
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
- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize Node.js project with n8n and PostgreSQL dependencies
- [ ] T003 [P] Configure linting (ESLint) and formatting (Prettier) tools

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**
- [ ] T004 [P] Contract test POST /reviews in tests/contract/test_reviews_post.py
- [ ] T005 [P] Contract test GET /reviews/{id} in tests/contract/test_reviews_get.py
- [ ] T006 [P] Contract test PUT /reviews/{id} in tests/contract/test_reviews_put.py
- [ ] T007 [P] Contract test POST /reviews/{id}/elements in tests/contract/test_elements_post.py
- [ ] T008 [P] Contract test GET /reviews/{id}/elements in tests/contract/test_elements_get.py
- [ ] T009 [P] Contract test GET /reviews/{id}/elements/{elementId} in tests/contract/test_elements_get_by_id.py
- [ ] T010 [P] Contract test PUT /reviews/{id}/elements/{elementId} in tests/contract/test_elements_put.py
- [ ] T011 [P] Contract test DELETE /reviews/{id}/elements/{elementId} in tests/contract/test_elements_delete.py
- [ ] T012 [P] Contract test POST /reviews/{id}/elements/{elementId}/errors in tests/contract/test_errors_post.py
- [ ] T013 [P] Contract test GET /reviews/{id}/report in tests/contract/test_report_get.py
- [ ] T014 [P] Integration test create review and add element in tests/integration/test_review_workflow.py
- [ ] T015 [P] Integration test generate report in tests/integration/test_report_generation.py

## Phase 3.3: Core Implementation (ONLY after tests are failing)
- [ ] T016 [P] UI Review Report model in src/models/UIReviewReport.js
- [ ] T017 [P] Non-Functional Element model in src/models/NonFunctionalElement.js
- [ ] T018 [P] Page Section model in src/models/PageSection.js
- [ ] T019 [P] Error Log Entry model in src/models/ErrorLogEntry.js
- [ ] T020 [P] Severity Classification lookup in src/models/SeverityClassification.js
- [ ] T21 POST /reviews endpoint implementation in src/services/reviewService.js
- [ ] T22 GET /reviews/{id} endpoint implementation in src/services/reviewService.js
- [ ] T23 PUT /reviews/{id} endpoint implementation in src/services/reviewService.js
- [ ] T24 POST /reviews/{id}/elements endpoint implementation in src/services/elementService.js
- [ ] T25 GET /reviews/{id}/elements endpoint implementation in src/services/elementService.js
- [ ] T26 GET /reviews/{id}/elements/{elementId} endpoint implementation in src/services/elementService.js
- [ ] T27 PUT /reviews/{id}/elements/{elementId} endpoint implementation in src/services/elementService.js
- [ ] T28 DELETE /reviews/{id}/elements/{elementId} endpoint implementation in src/services/elementService.js
- [ ] T29 POST /reviews/{id}/elements/{elementId}/errors endpoint implementation in src/services/errorService.js
- [ ] T30 GET /reviews/{id}/report endpoint implementation in src/services/reportService.js
- [ ] T31 Input validation for all endpoints in src/middleware/validationMiddleware.js
- [ ] T32 Error handling and logging in src/middleware/errorMiddleware.js

## Phase 3.4: Integration
- [ ] T33 Connect reviewService to PostgreSQL database
- [ ] T34 Connect elementService to PostgreSQL database
- [ ] T35 Connect errorService to PostgreSQL database
- [ ] T36 Auth middleware (if required) in src/middleware/authMiddleware.js
- [ ] T37 Request/response logging in src/middleware/loggingMiddleware.js
- [ ] T38 CORS and security headers in src/middleware/securityMiddleware.js

## Phase 3.5: Polish
- [ ] T39 [P] Unit tests for validation in tests/unit/test_validation.js
- [ ] T40 Performance tests (<2s response time)
- [ ] T41 [P] Update docs/api.md
- [ ] T42 Remove duplication
- [ ] T43 [P] Run manual testing checklist from quickstart.md

## Dependencies
- Tests (T004-T015) before implementation (T016-T032)
- T016 blocks T017, T033
- T017 blocks T018, T034
- T018 blocks T019, T035
- T019 blocks T036
- T033 blocks T037
- T037 blocks T038
- Implementation before polish (T39-T43)

## Parallel Example
```
# Launch T004-T015 together:
Task: "Contract test POST /reviews in tests/contract/test_reviews_post.py"
Task: "Contract test GET /reviews/{id} in tests/contract/test_reviews_get.py"
Task: "Contract test PUT /reviews/{id} in tests/contract/test_reviews_put.py"
Task: "Contract test POST /reviews/{id}/elements in tests/contract/test_elements_post.py"
Task: "Contract test GET /reviews/{id}/elements in tests/contract/test_elements_get.py"
Task: "Contract test GET /reviews/{id}/elements/{elementId} in tests/contract/test_elements_get_by_id.py"
Task: "Contract test PUT /reviews/{id}/elements/{elementId} in tests/contract/test_elements_put.py"
Task: "Contract test DELETE /reviews/{id}/elements/{elementId} in tests/contract/test_elements_delete.py"
Task: "Contract test POST /reviews/{id}/elements/{elementId}/errors in tests/contract/test_errors_post.py"
Task: "Contract test GET /reviews/{id}/report in tests/contract/test_report_get.py"
Task: "Integration test create review and add element in tests/integration/test_review_workflow.py"
Task: "Integration test generate report in tests/integration/test_report_generation.py"
```

## Notes
- [P] tasks = different files, no dependencies
- Verify tests fail before implementing
- Commit after each task
- Avoid: vague tasks, same file conflicts

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts**:
   - Each contract file → contract test task [P]
   - Each endpoint → implementation task

2. **From Data Model**:
   - Each entity → model creation task [P]
   - Relationships → service layer tasks

3. **From User Stories**:
   - Each story → integration test [P]
   - Quickstart scenarios → validation tasks

4. **Ordering**:
   - Setup → Tests → Models → Services → Endpoints → Polish
   - Dependencies block parallel execution

## Validation Checklist
*GATE: Checked by main() before returning*

- [ ] All contracts have corresponding tests
- [ ] All entities have model tasks
- [ ] All tests come before implementation
- [ ] Parallel tasks truly independent
- [ ] Each task specifies exact file path
- [ ] No task modifies same file as another [P] task
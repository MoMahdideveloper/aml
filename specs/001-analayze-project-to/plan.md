# Implementation Plan: Project Analysis & Future Suggestions

**Branch**: `001-analayze-project-to` | **Date**: 2025-09-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-analayze-project-to/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
4. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
5. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, or `GEMINI.md` for Gemini CLI).
6. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
7. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
8. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Implement an automated project analysis system that evaluates the Real Estate CRM codebase structure, identifies technical debt, assesses feature completeness, and generates prioritized suggestions for future improvements. The system will provide actionable recommendations to help stakeholders make informed decisions about project evolution and development priorities.

## Technical Context
**Language/Version**: Python 3.11+  
**Primary Dependencies**: Flask 3.0.0+, SQLAlchemy 2.0+, ChromaDB 0.4+, Google Generative AI  
**Storage**: SQLite (existing), potential file-based analysis cache  
**Testing**: pytest 7.0+ (existing test framework)  
**Target Platform**: Web application (existing Flask-based CRM)
**Project Type**: web - Flask backend with HTML templates (existing structure)  
**Performance Goals**: Analysis completion <30 seconds for typical CRM codebase  
**Constraints**: Must not interfere with existing CRM operations, read-only analysis  
**Scale/Scope**: Single Flask application, ~25 Python files, existing Real Estate CRM features

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: 1 (web app only - extends existing Flask CRM)
- Using framework directly? (yes - Flask, SQLAlchemy direct usage)
- Single data model? (yes - analysis entities only, leveraging existing CRM models)
- Avoiding patterns? (yes - direct service approach, no Repository pattern)

**Architecture**:
- EVERY feature as library? (no - integrating into existing Flask app structure)
- Libraries listed: analysis_service (codebase analysis), suggestion_engine (recommendation generation)
- CLI per library: N/A (web-based feature within existing Flask routes)
- Library docs: Will update existing CLAUDE.md with new analysis capabilities

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? (YES - contract tests defined in quickstart)
- Git commits show tests before implementation? (YES - planned workflow)
- Order: Contract→Integration→E2E→Unit strictly followed? (YES - defined in Phase 1)
- Real dependencies used? (YES - actual SQLite database, no mocks)
- Integration tests for: new libraries, contract changes, shared schemas? (YES - analysis service integration tests planned)
- FORBIDDEN: Implementation before test, skipping RED phase (ENFORCED)

**Observability**:
- Structured logging included? (YES - following existing Flask logging patterns)
- Frontend logs → backend? (YES - existing unified logging in place)
- Error context sufficient? (YES - comprehensive error handling planned)

**Versioning**:
- Version number assigned? (YES - 1.0.0 for analysis feature)
- BUILD increments on every change? (YES - following existing versioning)
- Breaking changes handled? (YES - additive changes only, no breaking changes)

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: Option 2 (Web application) - extending existing Flask CRM structure with new analysis modules

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `/scripts/update-agent-context.sh [claude|gemini|copilot]` for your AI assistant
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Contract test tasks for each API endpoint [P]
- Model creation tasks for 5 entities (AnalysisReport, SuggestionItem, etc.) [P]
- Service layer tasks for analysis engine and suggestion generator
- Web interface tasks for dashboard and management views
- Integration test tasks for complete workflows
- Export functionality tasks (PDF, Excel, JSON)

**Ordering Strategy**:
1. Contract tests (failing tests first - TDD)
2. Database models (AnalysisReport → SuggestionItem → supporting entities)
3. Analysis service layer (core business logic)
4. API endpoints (following contracts)
5. Web dashboard interface
6. Export functionality
7. Integration tests (end-to-end workflows)

**Estimated Output**: 28-32 numbered, ordered tasks covering models, services, APIs, UI, and tests

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*
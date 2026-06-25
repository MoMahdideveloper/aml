# Deep Think Stage PB3: Dual-Sided Scoring Engine

## Objective
Define deterministic customer and property priority scoring (`0-100`) with cheap daily recomputation and optional AI modifiers.

## Primary Question
How should we implement `customer_score` + `property_score` in this codebase so that:
- baseline scoring is pure DB math (cheap),
- AI intent modifier is batched async,
- scores are auditable, deterministic, and easy to tune,
- outputs directly drive lead prioritization and listing ranking?

## Required Output Format
1. Scoring formula spec:
   - customer scoring factors/weights
   - property scoring factors/weights
   - normalization strategy
2. Data model changes:
   - columns/tables
   - migration plan
   - historical snapshots for explainability
3. Batch architecture:
   - Celery tasks
   - beat schedule
   - idempotency keys
4. AI modifier contract:
   - input text budget strategy
   - output schema
   - fallback when AI unavailable
5. Rollout plan:
   - shadow mode
   - threshold gating (`Hot Lead`, `Rare Find`)
6. Tests:
   - deterministic ranking tests
   - regression tests for edge cases and stale data

## Constraints
- Do not run heavy AI scoring in request/response cycle.
- Keep score outputs deterministic for identical inputs.
- Keep backward compatibility for current recommendation flows.

## Context IDs
`PB-CTX-002`, `PB-CTX-003`, `PB-CTX-006`, `PB-CTX-007`, `PB-CTX-008`, `PB-CTX-009`, `PB-CTX-010`


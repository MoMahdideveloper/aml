# Deep Think Stage PB6: Final Execution Backlog (Wave Plan)

## Objective
Produce implementation-ready waves with dependencies, test gates, and rollback criteria.

## Primary Question
Given PB1-PB5 outputs and the attached context, provide a final delivery plan in 3 waves:
- Wave 1: Security + contracts + foundation
- Wave 2: Scoring + smart context + matchmaker UX
- Wave 3: Weekly intelligence + optimization + cleanup

## Required Output Format
1. Backlog table with:
   - `priority` (P0/P1/P2)
   - `task`
   - `files`
   - `dependencies`
   - `risk`
   - `tests_required`
   - `rollback_check`
2. Explicit migration plan (DB + data backfill).
3. Explicit API contract checklist.
4. Explicit acceptance criteria for “done”.
5. “First 10 commits” suggestion list.

## Constraints
- Keep Stage P5 guarantees (auth/CSRF/fallback determinism).
- Keep current app stable during phased rollout.
- Avoid wide refactors in a single wave.

## Context IDs
`PB-CTX-001` to `PB-CTX-015`


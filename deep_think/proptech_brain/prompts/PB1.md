# Deep Think Stage PB1: Architecture Delta Mapping

## Objective
Merge the new product vision into the current `gptvli` codebase without breaking existing contracts.

## Primary Question
Given the attached context chunks (`PB-CTX-*`), what is the minimum dependency-ordered architecture delta to evolve `gptvli` into an autonomous PropTech engine with:
- Smart Context benefits
- Dual-sided scoring (customer/property)
- Matchmaker + Copilot pitch drafting
- Weekly trends/training pipeline

## Constraints (Must Respect)
- API/XHR unauthorized => `401/403` JSON only.
- Keep CSRF enforced for new core endpoints.
- No redirect leakage for API requests.
- Deterministic fallback for Gemini/vector failure.
- Heavy AI and batch scoring must run async (Celery/beat), not request path.
- Preserve existing routes/contracts unless explicitly versioning new endpoints.

## Required Output Format
1. A dependency-ordered architecture table:
   - `component`
   - `current_state`
   - `gap`
   - `minimal_change`
   - `risk`
   - `depends_on`
2. A file-level change map (exact files to touch first).
3. A “do-not-touch yet” list to avoid regressions.
4. Top 10 acceptance tests (integration/e2e mix).

## Context IDs
`PB-CTX-001` to `PB-CTX-015`


# Deep Think Stage PB4: Matchmaker + Copilot Endpoint/UI

## Objective
Design a secure and deterministic Matchmaker flow that pairs high-priority customers with high-priority listings and drafts agent-ready outreach text.

## Primary Question
What is the best implementation for `/api/v1/copilot/matchmaker/<customer_id>` and corresponding UI integration so that:
- endpoint returns structured match + pitch payload,
- unauthorized API calls return JSON `401/403` (no redirects),
- CSRF and `X-Requested-With` contracts are preserved,
- JS modal lifecycle remains stable under heavy usage,
- Gemini failure still returns deterministic usable fallback pitch text.

## Required Output Format
1. API contract:
   - request shape
   - response schema
   - error schema
2. Auth/CSRF behavior matrix (browser vs XHR).
3. Matching + pitch generation flow:
   - score filtering
   - reasoning composition
   - fallback copy generation
4. Frontend integration plan:
   - where to add badges/buttons
   - event lifecycle and cleanup
   - toast/error UX
5. Test plan:
   - auth security
   - contract tests
   - modal stability tests

## Constraints
- No new blanket `@csrf.exempt` usage.
- Preserve existing recommendation endpoints while introducing versioned matchmaker API.
- Return explicit fallback metadata in degraded mode.

## Context IDs
`PB-CTX-001`, `PB-CTX-005`, `PB-CTX-006`, `PB-CTX-007`, `PB-CTX-011`, `PB-CTX-013`, `PB-CTX-014`, `PB-CTX-015`


# Deep Think Stage PB2: Smart Context Engine (Multimodal + Silver Lining)

## Objective
Design a one-time enrichment pipeline that converts raw listing facts into buyer-friendly “silver lining” benefits and trend badges.

## Primary Question
Based on current `Property` schema and Gemini provider/service implementation, what is the best production design for a Smart Context Engine that:
- runs on listing create/update and image upload (not every page load),
- generates strict JSON (`smart_benefits`, `trending_badges`, confidence metadata),
- stores cached output in DB,
- gracefully degrades with deterministic fallback.

## Required Output Format
1. JSON schema contract for `analyze_multimodal_context()` output.
2. Prompt template for Gemini (strict JSON, no prose).
3. Storage design:
   - reuse vs new table decision
   - indexes
   - migration steps
4. Trigger model:
   - synchronous trigger points
   - async task queue execution
5. Failure contract:
   - timeout/error fallback payload
   - retry policy
6. Test matrix:
   - unit
   - integration
   - e2e/UI verification

## Hard Constraints
- No 500 for handled AI failure.
- Keep existing listing response shape compatible.
- API endpoints must preserve auth/CSRF contracts.

## Context IDs
`PB-CTX-002`, `PB-CTX-004`, `PB-CTX-005`, `PB-CTX-009`, `PB-CTX-010`, `PB-CTX-011`, `PB-CTX-012`


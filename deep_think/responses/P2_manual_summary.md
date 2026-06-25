# P2 Deep Think Response (Captured Summary)

## 1) Root-Cause Map

- Shared root cause: CSRF token context is missing at render time and request failures are not handled safely on the frontend.
- Secondary cause A: API error responses can be HTML while frontend assumes JSON, causing parsing crashes and JS flow breakage.
- Secondary cause B: Modal/event handlers are bound too statically; dynamically added DOM nodes miss handlers.

Evidence focus:
- `templates/base.html` (missing CSRF meta source)
- `static/js/crud-utils.js` (request wrapper + response parsing path)
- `app.py` and `views/properties.py` (error response behavior)
- `static/js/main.js` (modal/event delegation behavior)

## 2) Ordered Remediation Sequence

1. Add CSRF token source in base template head.
2. Patch `crud-utils` request wrapper to attach CSRF and guard JSON parsing.
3. Add app-level CSRF/auth JSON error handling path for AJAX consumers.
4. Refactor modal and action bindings to delegated handlers.

## 3) Step-to-Failure Mapping

- Step 1: addresses prerequisites behind TC001/TC003 mutation/edit failures.
- Step 2: addresses TC004/TC005/TC012 interaction failures and crash chain.
- Step 3: addresses TC010/TC013 error-contract mismatch.
- Step 4: addresses TC007/TC009/TC014 UI routing/state sync issues.

## 4) Validation Matrix

- Unit: CSRF rejection returns JSON contract, not HTML for AJAX paths.
- Integration: outbound AJAX includes `X-CSRFToken`; non-JSON response handling does not crash.
- E2E: create/update/delete modal flows and notification mark-read update state reliably.
- Possible testsprite false-positive: modal close timing assertions during CSS transitions; verify with hidden-state waits rather than instant DOM removal expectation.

## 5) Guardrails

- Do not disable CSRF globally.
- Do not change public route/API contracts for this fix set.
- Do not replace fetch stack/framework as part of critical-path patch.
- Do not alter modal CSS/ID contracts unless strictly required.

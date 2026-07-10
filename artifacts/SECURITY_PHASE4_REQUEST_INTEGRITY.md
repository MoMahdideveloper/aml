# Security Phase 4 — CSRF, Input Validation, XSS

**Date:** 2026-07-10  
**Branch:** `005-template-replacement`

---

## Tests

| File | Focus |
|------|--------|
| `tests/test_security_csrf.py` | ENABLE_CSRF=1 mutations blocked without token |
| `tests/test_csrf_frontend_contract.py` | Agents / property AI / main.js CSRF headers |
| `tests/test_security_input_validation.py` | Form boundaries + malformed IDs |
| `tests/test_security_xss.py` | Stored XSS escaped; `\|safe` inventory |

**Suite:** 29+ related tests green; CI core job includes these files.

---

## CSRF (Task 9)

| Behavior | Result |
|----------|--------|
| `ENABLE_CSRF=1` / production default | `CSRFProtect(app)` registered |
| Forms use `BaseNoCSRFForm` | Form-level CSRF off; **app-level** CSRFProtect still enforces |
| Missing/invalid token | No DB mutation; HTML often 302 → dashboard via 400 handler |
| Valid `csrf_token` field or `X-CSRFToken` | Mutation succeeds |
| Frontend | Meta `csrf-token` in `base.html`; agents fetch, property AI helper, AI autofill send header |

### Frontend fixes this phase

- `templates/agents.html` — edit fetch: `X-CSRFToken` + `credentials: 'same-origin'`
- `templates/property_details.html` — `propertyAiFetch()` helper with CSRF headers
- `static/js/main.js` — implemented `initializeAIAutofill()` with CSRF + same-origin

---

## Input validation (Task 10)

WTForms `DataRequired` / `Email` / `Length` / `NumberRange` reject bad customer/agent/deal/task posts without writing rows. Malformed integer path segments do not return 500 stack traces.

**Note:** Error UX is flash + redirect (200 after follow) rather than strict 422 JSON for HTML forms — acceptable for server-rendered CRM; API CSRF failures return JSON 400 for XHR.

---

## XSS (Task 11)

| Area | Assessment |
|------|------------|
| Jinja autoescape | Escapes stored `<script>` on list pages |
| JSON APIs | Content-Type JSON; raw strings OK for clients that don't `innerHTML` blindly |
| `\|safe` uses | Only `map_view` `properties_json`, modal content/footer — inventory test locks this |
| `static/js` `innerHTML` | Toasts/loading use fixed strings; analysis.js builds DOM from API — monitor if user HTML ever injected |

---

## Commands

```powershell
python -m pytest -q tests/test_security_csrf.py tests/test_security_input_validation.py tests/test_security_xss.py tests/test_csrf_frontend_contract.py
```

---

## Next (Phase 5)

Sensitive serialization, admin env secret handling, LLM/outbound boundaries (Tasks 12–14).

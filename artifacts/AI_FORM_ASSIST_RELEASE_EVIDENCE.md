# AI Form Assist — Release Evidence

**Date:** 2026-07-13  
**Branch:** `005-template-replacement`  
**Runner:** local agent (not production, no deployment, no live Gemini calls)

---

## 1. Full AI form test suite

**Command:**
```
python -m pytest tests/test_ai_form_*.py -v --tb=short
```

**Result:** 85 passed, 1 skipped

| File | Result |
|------|--------|
| test_ai_form_api.py | passed |
| test_ai_form_audit_models.py | passed |
| test_ai_form_confidence.py | passed |
| test_ai_form_customer_ui.py | passed |
| test_ai_form_deal_task_ui.py | passed |
| test_ai_form_failure_modes.py | passed |
| test_ai_form_gemini_extractor.py | 4 passed, 1 skipped* |
| test_ai_form_mock_extractor.py | passed |
| test_ai_form_normalization.py | passed |
| test_ai_form_property_ui.py | passed |
| test_ai_form_provider_smoke.py | 30 passed |
| test_ai_form_retention.py | passed |
| test_ai_form_schema_registry.py | passed |
| test_ai_form_security.py | passed |
| test_ai_form_storage.py | passed |
| test_ai_form_agent_ui.py | passed |

\* `test_build_parts_includes_image_and_audio` skipped: `pytest.importorskip("google.genai")` — package not installed in local env. Not a regression; this skip is intentional and pre-existing.

---

## 2. Mock provider smoke CLI

**Command:**
```
python -m pytest tests/test_ai_form_provider_smoke.py -v
```

**Result:** 26 passed — mock mode, live-guard, and in-process API all verified. No DB writes. No live Gemini calls. No sensitive values in output.

---

## 3. Track A UI suite

**Command:**
```
python -m pytest tests/ -k "platinum_heritage_ui or app_smoke or template_replacement or accessibility_shell" --ignore=tests/test_crud_forms.py --ignore=tests/test_customers_template.py --ignore=tests/test_deals_template.py --ignore=tests/unit/test_device_detector.py -v --tb=short
```

**Result:** 67 passed

---

## 4. Security and production config suite

**Command:**
```
python -m pytest tests/ -k "auth_default_deny or authz_deny_first or security_csrf or csrf_frontend_contract or production_config or health_readiness" --ignore=tests/test_crud_forms.py --ignore=tests/test_customers_template.py --ignore=tests/test_deals_template.py --ignore=tests/unit/test_device_detector.py -v --tb=short
```

**Result:** 40 passed

Covers: auth default-deny, authz deny-first, CSRF backend, CSRF frontend contract, production config (session secret, secure cookies, security headers, AI form defaults-off), health/readiness endpoints.

---

## 5. Mock vs live distinction

| Mode | Command | Gemini calls | DB writes | Key required |
|------|---------|-------------|-----------|-------------|
| Mock (automated) | `python -m pytest tests/test_ai_form_provider_smoke.py` | None | None | No |
| Mock (CLI) | `python scripts/verify_ai_form_provider.py --mode mock` | None | None | No |
| Live (manual only) | `AI_FORM_LIVE_SMOKE=1 python scripts/verify_ai_form_provider.py --mode live` | Yes | Yes | Yes |

**No live calls are permitted in CI.** The explicit `AI_FORM_LIVE_SMOKE=1` environment gate is the deliberate friction point enforced in `scripts/verify_ai_form_provider.py`. Tests `TestLiveModeGuard::test_live_without_flag_exits_nonzero` and `test_live_with_flag_but_no_credentials_exits_nonzero` verify this contract.

---

## 6. Browser smoke

`tests/test_browser_smoke.py` — **file does not exist** in this branch.

Browser smoke was previously recorded in `docs/AI_FORM_ASSIST_OPERATOR.md` under "Browser smoke (2026-07-13, mock mode)" based on a prior manual run. That prior run observed: login → properties page → modal AI panel → mock extraction (HTTP 201) → suggestions (title, bedrooms, bathrooms, etc.) → auto-fill of empty fields. Screenshots at `artifacts/ai-form-assist-property-mock-smoke.png` and `artifacts/ai-form-assist-property-mock-smoke-mobile.png`.

**Status:** Skipped in this gate run. Reason: no `test_browser_smoke.py` exists; browser E2E requires a running server and is designated a human checkpoint (Checkpoint C/D).

---

## 7. Pre-existing syntax failures (unrelated to AI form assist)

The following test files have syntax errors pre-dating this branch and are excluded from all runs above:

| File | Error |
|------|-------|
| `tests/unit/test_device_detector.py` | `SyntaxError: unterminated triple-quoted string literal (line 1)` |
| `tests/test_crud_forms.py` | Collection error (syntax) |
| `tests/test_customers_template.py` | `SyntaxError: unmatched ')' (line 150)` |
| `tests/test_deals_template.py` | `SyntaxError: closing parenthesis '}' does not match '[' (line 155)` |

These are not caused by AI form assist changes.

---

## 8. Remaining human approval gates

The following items are deliberately unchecked and require human action:

- [ ] Human approves registry before provider/database work (Checkpoint A)
- [ ] Human approves migration, storage, and 90-day retention before API/UI (Checkpoint B)
- [ ] Human approves Property UX before expansion (Checkpoint C)
- [ ] Desktop/mobile/accessibility review passes (Checkpoint D)
- [ ] Human separately approves any commit, push, production migration, or deployment (Final Gate)

No commit, push, deployment, or production migration was performed during this gate run.

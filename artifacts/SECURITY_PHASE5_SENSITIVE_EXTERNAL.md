# Security Phase 5 — Sensitive Data & External Boundaries

**Date:** 2026-07-10  
**Tests:** `tests/test_security_sensitive_data.py` (13)

---

## Task 12 — Serialization

| Check | Result |
|-------|--------|
| `User.to_dict()` | No `password_hash` / `password` |
| CRM JSON APIs | No password hashes, no default session secret |
| 500 JSON | Generic message; no traceback / internal paths |
| Health probes | No secrets |

---

## Task 13 — Admin environment

| Control | Status |
|---------|--------|
| CRM session ≠ admin | Enforced (middleware + `require_admin_auth`) |
| Sensitive list/details | Masked (`***` style via `to_dict(mask_sensitive=True)`) |
| Change log for secrets | Stores `***` for sensitive creates/updates |
| Protected keys | `*_API_KEY`, SESSION_SECRET, DATABASE_URL, … not DB-managed |
| Client error leakage | Hardened: unexpected admin errors no longer flash/JSON `str(e)` |
| Result unwrap | Views now handle `Success` / `RetryableError` / `PermanentError` from config service (was treating Result as dict → 500) |

**Remaining residual risk:** Admin who can set env values still applies them to `os.environ` at runtime; treat admin as full privilege.

---

## Task 14 — LLM / outbound

| Control | Status |
|---------|--------|
| Extract tests | Fakes only; empty text → 400; provider fail → generic 500 |
| Timeouts | KIE + Gemini request timeouts configured |
| Geocode SSRF | Fixed Nominatim host; user text is `q=` only |
| Model output | Returned as JSON data; not eval'd/shell'd |

**Open recommendations (no policy change without approval):**

1. Cap extract text length (e.g. 20k chars) before calling provider.
2. Do not allow untrusted users to set `KIE_CHAT_COMPLETIONS_URL` / base URLs (admin-only process env).
3. Redact known secret patterns from LLM prompts if customer notes may contain credentials.

---

## Commands

```powershell
python -m pytest -q tests/test_security_sensitive_data.py
```

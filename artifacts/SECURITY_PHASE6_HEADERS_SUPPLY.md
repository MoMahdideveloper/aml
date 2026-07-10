# Security Phase 6 — Headers & Supply Chain

**Date:** 2026-07-10

---

## Task 15 — Response headers

| Header | Dev | Production |
|--------|-----|------------|
| `X-Content-Type-Options: nosniff` | yes | yes |
| `X-Frame-Options: DENY` | yes | yes |
| `Referrer-Policy: strict-origin-when-cross-origin` | yes | yes |
| `X-XSS-Protection: 0` | yes | yes (modern browsers) |
| `Permissions-Policy` (geo/mic/cam/payment off) | yes | yes |
| `Content-Security-Policy` | opt-in `ENABLE_CSP=1` | on |
| `Strict-Transport-Security` | off | on |
| `Cache-Control: no-store…` on `/auth/*`, `/admin/*` | yes | yes |

CSP allows self + PH CDN fonts/Tailwind/unpkg + Nominatim `connect-src`. No `default-src *` / `script-src *`.

**Tests:** `tests/test_security_headers.py`, `tests/test_production_config.py::test_production_security_headers`.

---

## Task 16 — Dependencies & secret scan

### Lockfiles

| File | Status |
|------|--------|
| `requirements.txt` | Present (uv-exported) |
| `uv.lock` | Present |
| `package-lock.json` | Present (root Tailwind) |

**Note:** `pip-audit` not installed in this environment. Recommended periodic command (human/CI optional job):

```powershell
pip install pip-audit
pip-audit -r requirements.txt
npm audit --omit=dev
```

Document critical/high from those tools with owner + date when first run in CI.

### Secret scan

```powershell
python scripts/scan_secrets.py --out artifacts/SECRET_SCAN.json
```

- **Never prints secret values** — path, line, pattern name only.
- Exit code **1** if any **high** findings remain.
- Latest run: **high=0**, medium=1 (`n8n_data.md` bearer-like literal — review/rotate if real), low≈45 mostly default-password **hints** in tests/docs/code (`admin123`, `password123`, dev secret string).

**Action:** If `n8n_data.md` ever held a live token, rotate it and scrub the file. Prefer process env for all real credentials.

**Tests:** `tests/test_security_secret_scan.py`.

---

## Phase 7 seed (this batch)

| Item | Status |
|------|--------|
| `utils/security_events.py` | Structured `security.events` logger + redaction |
| Login success/failure + logout | Emits events without passwords |
| CI | Security test files + `scan_secrets.py` gate |

---

## Commands

```powershell
python -m pytest -q tests/test_security_headers.py tests/test_security_secret_scan.py tests/test_security_events.py tests/test_production_config.py
python scripts/scan_secrets.py --out artifacts/SECRET_SCAN.json
```

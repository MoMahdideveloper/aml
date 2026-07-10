# Security Phase 3 — Authorization / Object Isolation

**Date:** 2026-07-10  
**Branch:** `005-template-replacement`  
**Tests:** `tests/test_authz_deny_first.py` (14 passed)

---

## Access model (actual product)

```text
Anonymous ──deny──► login / 401
     │
Authenticated User (user_id) ──► global CRM data (all rows)
     │                              roles agent|viewer stored, not enforced
Admin (admin_authenticated) ──► /admin/* environment tools only
```

This is a **single-office / global staff CRM**, not multi-tenant SaaS.

| Check | Result |
|-------|--------|
| Anon can read customers/properties/deals/… | **No** (with `AUTH_DEFAULT_DENY_ENABLED=1`) |
| Staff A can read staff B’s customer by ID | **Yes** — intentional |
| Staff A can mutate shared deal | **Yes** — intentional |
| Staff user can open `/admin/environment` without admin login | **No** |
| `viewer` role limited to read-only | **No** (F6) |

---

## What was implemented

| Item | Action |
|------|--------|
| Deny-first tests | HTML lists, API GETs, mutations for anon |
| Global-model contract tests | Second user + viewer can load same IDs |
| Admin isolation | CRM session ≠ admin session |
| Logout revocation | API 401 after logout |
| Ownership / tenancy code | **Not added** (would invent multi-tenancy) |
| New permission decorator | **Not needed** — auth centralized; no ownership rule |

---

## Findings

| ID | Severity | Notes |
|----|----------|-------|
| F2 | accepted risk | Global data among staff — document for operators |
| F6 | low | `user_role` unused for authorization |
| F5 | high | Still open from Phase 2 (login rate limits) |

---

## Optional product decisions (human)

1. Keep global staff CRM (**current**), or design ownership scopes.
2. Enforce `viewer` as read-only (would need route-level role checks).
3. Approve login rate-limit table from Phase 2 findings.

---

## Commands

```powershell
python -m pytest -q tests/test_authz_deny_first.py tests/test_auth_default_deny.py tests/test_auth_lifecycle.py
```

# AI Form Assist — Operator guide

Multimodal form suggestions (text / image / audio) for CRM create/edit forms.
**Suggestions only** — AI never writes Property, Customer, Deal, Task, or Agent rows.
Users accept/reject fields and submit the normal form.

## Feature flag

| Env | Default | Meaning |
|-----|---------|---------|
| `ENABLE_AI_FORM_ASSIST` | `0` | Master switch. API returns 404 when off; panels still render but processing fails closed. |
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | unset | Required for live Gemini extraction when feature is on. |
| `AI_FORM_AUDIT_STORAGE_ROOT` | `instance/ai_form_audit` | Private media directory (**must not** be under `static/`). |
| `AI_FORM_RETENTION_DAYS` | `90` | Age after which audit extractions are eligible for purge. |
| `AI_FORM_RETENTION_SCHEDULE_ENABLED` | `0` | When `1`, Celery Beat schedules nightly purge (`crm.cleanup_ai_form_audit`). |
| `AI_FORM_FAST_MODEL` | provider default | Optional model id override. |

Copy from `.env.example`. Invalid or missing AI keys must not prevent CRM startup when the flag is off.

## Enable (staging)

1. `flask db upgrade` (audit tables migration).
2. Set `ENABLE_AI_FORM_ASSIST=1` and a valid Gemini API key.
3. Ensure `AI_FORM_AUDIT_STORAGE_ROOT` is a private path outside `static/`.
4. Restart web workers.
5. Smoke: open Properties → Add property → AI form assist panel → text notes → Process (consent required).

## API (authenticated session)

- `POST /api/ai-form-assist/extractions` — multipart or JSON; form name + text/media.
- `GET /api/ai-form-assist/extractions/<id>`
- `POST /api/ai-form-assist/extractions/<id>/review` — accept/reject/edit/undo decisions only.

Disabled flag → HTTP 404. Unauthenticated → 401. Unknown form schema → 400.

## Data sent to Gemini

- User-provided text notes and uploaded image/audio for the request.
- Schema field names (allowlist) for structured JSON extraction.
- **Not** sent: full CRM database dumps, session secrets, or other users’ records.

## Retained audit content

| Store | Content |
|-------|---------|
| DB `ai_form_extractions` | form, actor id/label, status, model id, sizes/mimes meta (no raw body by design). |
| DB `ai_form_media` | storage key, sha256, mime, size, original filename string. |
| Disk under audit root | Binary media; server-generated paths only. |
| DB suggestions / decisions | Field names, confidence, actions, review decisions. |

Logs/metrics must stay content-free (no raw notes, transcripts, phones, emails, API keys).

## Retention cleanup

Callable service (no hidden Flask threads):

```python
from services.ai_form_assist.retention import cleanup_expired_ai_form_audit

# Safe inventory
cleanup_expired_ai_form_audit(dry_run=True)

# Authorized purge (media files first, then rows)
cleanup_expired_ai_form_audit(dry_run=False, limit=200)
```

Celery task: `crm.cleanup_ai_form_audit` (optional Beat when `AI_FORM_RETENTION_SCHEDULE_ENABLED=1`).

CRM entities are never deleted by retention.

## Forms covered

Registry schemas: `property`, `customer`, `recommendation`, `deal`, `task`, `agent`.
Relationship IDs (`agent_id`, `property_id`, `customer_id`) are review-only / never auto-fill.

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Panel missing | Template include + `ai-form-assist.js` on page. |
| Process → 404 | `ENABLE_AI_FORM_ASSIST=1` and app restarted. |
| Process → 401 | User session / login. |
| Process → empty suggestions | Mock vs live Gemini; consent checkbox; text/media present. |
| Storage errors | Root not under `static/`; disk space; permissions. |
| Ordinary save fails | Unrelated — AI path never replaces form POST handlers. |

## Cost controls

- Keep flag off until staging review is complete.
- Prefer short notes and few images (size caps in storage layer).
- Automated tests mock Gemini — no live paid calls in CI.
- Retention reduces long-lived media storage.

## Security notes

- Private media is not served as static assets.
- CSRF token expected on review JSON posts from the browser.
- Existing non-empty form fields are never auto-overwritten.
- Human save remains the only CRM write path.

## Release gate evidence (2026-07-13, branch `005-template-replacement`)

Observed on local agent run (not production):

| Gate | Result |
|------|--------|
| AI form suite (`tests/test_ai_form_*.py`) | **50 passed, 1 skipped** |
| Track A UI (`test_platinum_heritage_ui`, `test_app_smoke`, `test_template_replacement`, `test_accessibility_shell`) | **67 passed** |
| Security/config (`auth_default_deny`, `authz_deny_first`, `security_csrf`, `csrf_frontend_contract`, `production_config`, `health_readiness`) | **40 passed** |
| Disposable Alembic | head `a1b2c3d4e5f6`; upgrade → downgrade to `z1a2b3c4d5e6` → re-upgrade **OK** |
| `test_gemini_provider_multimodal` | **passed** |
| `test_forms_templates` | **pre-existing fail** (`Form submissions with new templates not implemented`) — not caused by AI form assist |
| Live Gemini smoke | **skipped** (no paid calls in gate) |
| Browser E2E at 1440×900 / 390×844 | **not run** — human Checkpoint C/D |

Feature remains **default off** (`ENABLE_AI_FORM_ASSIST=0`).

### Staging enable (human)

1. `flask db upgrade` to head `a1b2c3d4e5f6`
2. Set `ENABLE_AI_FORM_ASSIST=1`, Gemini key, private `AI_FORM_AUDIT_STORAGE_ROOT`
3. Restart web; smoke Property text path with consent
4. Review accept/reject/undo; confirm normal Property save still works
5. Optionally extend to Customer/Deal/Task/Agent panels
6. Keep retention schedule off until first dry-run:  
   `cleanup_expired_ai_form_audit(dry_run=True)`

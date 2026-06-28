# Real Estate CRM — Architecture Codemap

**Source:** Six parallel Explore-agent reports (routes, models, services, templates, forms, config).
**Branch:** `005-template-replacement`
**Date:** 2026-06-27

A flat reference. Cross-domain concerns at the bottom.

---

## 1. Application Surface

- **Entry / factory:** `app.py:14` `create_app()`; module-level `app = create_app()` at `app.py:151` (runs init_db + env loader + blueprint imports at import time — risky for WSGI re-importers).
- **Blueprint registrations:** `app.py:82-107`.
- **Alias rules:** `app.py:111-130` (old route names → new handlers).
- **Error handlers:** none registered; defaults apply.

### Registered blueprints

| Blueprint | URL prefix | Auth | Notes |
|---|---|---|---|
| `main` | none | none | dashboard, recommendations, api_market_analysis — all unauth |
| `properties` | none | none | full CRUD + read of PII unauth |
| `agents` | none | none | full CRUD + IDOR on edit/delete unauth |
| `customers` | none | none | full CRUD unauth |
| `deals` | none | none | full CRUD + IDOR on update unauth |
| `tasks` | none | none | full CRUD + IDOR on complete unauth |
| `admin_environment` | `/admin` | `@require_admin_auth` | session-based, trusts `ADMIN_PASSWORD` env (default `admin123`) |
| `notifications` | none | none | full notification API unauth, including mass-broadcast |
| `vector_api` | `/api/vector` | none | leaks persistence paths |
| `automations` | none | `@require_admin_auth` | only protected surface |
| `auth` | `/auth` | manual session check | uses `session.get("user_id")`, not `@login_required` |

### Orphaned blueprints (file exists, NOT registered in `app.py`)

- `views/analysis.py`
- `views/analytics.py`
- `views/rag.py` — **highest concern**: `rag_query` would build AI prompts containing all CRM data, currently unreachable

### Hot routes (security)

- `POST /properties/add`, `POST /agents/add`, `POST /customers/add`, `POST /deals/add`, `POST /tasks/add` — all unauthenticated writes
- `POST /agents/<id>/edit`, `POST /agents/<id>/delete`, `POST /deals/<id>/update`, `POST /tasks/<id>/complete`, all `/api/agents/<id>/notifications/*` — IDOR-prone
- `POST /api/notifications/system`, `POST /api/admin/notifications/broadcast` — unauthenticated injection of system-wide messages

---

## 2. Data Model (`sqlalchemy_models.py`)

24 models across 6 domains: core CRM, property support, customer segmentation, notifications, AI/observability, automation, env config, sync, SMS, auth.

### Core entities (soft-delete enabled)

| Model | Table | Soft-delete cols | Indexed? |
|---|---|---|---|
| `Property` | `properties` | `is_deleted`, `deleted_at` | `is_deleted` indexed |
| `Agent` | `agents` | same | same |
| `Customer` | `customers` | same | same |
| `Deal` | `deals` | same | same |
| `Task` | `tasks` | same | same |

**Soft-delete usage is partial:** queries in `services/database_service.py` must explicitly filter `is_deleted=False`. No global event listener enforces it.

### FK columns WITHOUT explicit index (SQLite masks; Postgres/MySQL hurt)

| Table.column | Severity |
|---|---|
| `property_images.property_id` | high |
| `contact_reveals.property_id` | medium |
| `customers.customer_group_id` | low |
| `deals.property_id` | **high** (hot path) |
| `deals.customer_id` | **high** (hot path) |
| `deals.agent_id` | high |
| `tasks.agent_id` | high |
| `properties.agent_id` | **high** (filter-by-agent) |
| `property_matches.property_id` | high |
| `property_matches.customer_id` | high |
| `property_matches.agent_id` | high |
| `property_ai_history.property_id` | medium |
| `agent_notifications.agent_id` | high |
| `agent_notifications.property_match_id` | high |
| `automation_audit_log.rule_id` | medium |
| `environment_change_log.environment_variable_id` | low |
| `ai_metadata.{property_id,customer_id,deal_id,task_id}` | medium |
| `sms_outbound_messages.created_by_user_id` | low |

### Cascade behavior

Only `PropertyMatch.notifications -> AgentNotification` uses `cascade="all, delete-orphan"`. All other 1:N relationships use default save-update — no delete cascade. Soft-delete on parents leaves orphans.

---

## 3. Form Layer (`forms.py`)

### WTForms classes

| Form | CSRF | Bound to | Gaps |
|---|---|---|---|
| `AgentForm` | **no** | `/agents/add`, `/agents/<id>/edit` | phone `Length(max=50)` vs DB `String(20)` |
| `CustomerForm` | **no** | `/customers/add` | phone drift; no cross-field `min>max` on budget |
| `PropertyForm` | **no** | `/properties/add` | no `SelectField` on enum strings (type/condition/category); missing ~30 DB columns |
| `DealForm` | **no** | `/deals/add` | `status`/`priority` free-form; `agent_id` required but DB nullable |
| `TaskForm` | **no** | `/tasks/add` | `priority` free-form; `due_date` is raw `StringField` |
| `EnvironmentVariableForm` | yes | `/admin/environment` | only form with CSRF |

### Raw form usage (no WTForms class)

- `/deals/<id>/update` — `request.form` direct
- `/auth/login`, `/auth/register`, `/auth/profile`, `/auth/change-password` — manual validation

### Form/model drift (representative)

- `Phone: form Length(max=50)` vs DB `String(20)` — silent truncation at DB
- `FloatField` on `BigInteger` columns: `Property.price/rahn/ejare`, `Customer.budget_min/max`, `Deal.offer_amount` — implicit float→int cast
- `PropertyForm` missing ~30 model columns (heating/cooling, rental_price, file_code, lat/lng, is_ai_extracted, source, is_deleted, etc.) — `edit` path can't update them

### CSRF posture

- `CSRFProtect` loads only when `ENABLE_CSRF=1` env var set (default OFF).
- 5 of 6 forms extend `BaseNoCSRFForm` (`csrf=False`).
- Effect: in default config, **every POST endpoint is CSRF-vulnerable**.

---

## 4. Templates & Static

- 47 `.html` files; root layout `base.html` (loads `stitch.css`, `style.css`, Tailwind CDN, FontAwesome 6.4.0, IBM Plex Sans).
- Inheritance: `customers.html`, `properties.html`, `deals.html`, `dashboard.html`, `agents.html`, `mobile/agents.html` extend `get_template_variant('base.html')`.
- Partials: `partials/{_header,_sidebar,_copilot,toast_notifications,view_option_selector}.html`.
- Modals: 14 modal partials under `modals/`. **`modals/base_modal.html:53,70` use `{{ content|safe }}` and `{{ footer|safe }}`** — XSS sinks if caller passes unescaped HTML.

### Static assets

- `/static/css/` — 4 files
- `/static/js/` — 11 files (analysis.js, button-fixes.js, crud-utils.js, dual-view-handler.js, main.js, property-edit-modal.js, recommendations.js, url-fix.js, etc.)
- `/static/images/` — 1 file (`default-avatar.png`)
- `favicon.ico` referenced in `base.html` but NOT present

### Inline JS/CSS

~30 templates contain inline `<style>` and `<script>` blocks. Migration to external bundles is incomplete.

---

## 5. Services Layer

13 service modules + 6 provider modules (LLM, SMS, embeddings).

### Key services

| Module | Surface | Notes |
|---|---|---|
| `services/database_service.py` | full CRUD on all entities | `@with_transaction()` decorator for mutations |
| `services/gemini_service.py` | recommendations, market analysis, multimodal extraction, RAG chat | module-level singleton; sync HTTP, no async batching |
| `services/vector_service.py` | property embedding search | pgvector + local fallback |
| `services/search_service.py` | unified search facade | always returns `meta.is_fallback` on error |
| `services/automation_service.py` | trigger→action rules | invoked from `DatabaseService.update_deal` |
| `services/notification_service.py` | agent notifications + email | **SMTP inline on request path** (create_property_match_notification) |
| `services/environment_service.py` | DB-backed env vars + runtime apply | writes `os.environ` directly |
| `services/favorites_service.py` | property favorites | clean, uses `@with_transaction()` |
| `services/workflow_service.py` | document processing | PDF path is placeholder |
| `services/sms_service.py` | SMS queue | Melipayamak + Log providers |
| `services/scheduler_service.py` | Celery beat jobs | 6 jobs: matching, rematch, cleanup, digest, overdue, SMS |
| `services/maskan_live_service.py` | external Maskan REST | sync HTTP, no batch parallelization |
| `services/monitoring_service.py` | observability | never raises |

### Logic-in-routes (smells)

- `views/properties.py:properties` — 80+ lines raw SQL + facet computation + agent_name `setattr` loop
- `views/properties.py:add_property` — inline sale/rental price rule logic
- `views/deals.py:update_deal` — manual float parsing, builds updates dict
- `views/tasks.py:add_task` — inline `strptime` parsing
- `views/customers.py:customers` — N+1 `setattr` for `total_deals/active_deals`
- `views/main.py:dashboard` — N+1 `setattr` on recent deals/tasks
- `views/rag.py:rag_query` — 110 lines inline DB queries + prompt assembly + AI call (orphaned but ready)
- `views/notifications.py:cleanup_agent_notifications` — inline query+delete loop
- `views/notifications.py:mark_all_notifications_read` — N+1 single-row updates
- `views/notifications.py:broadcast_system_notification` — N+1 single-row creates

### Blocking IO on request path

- `notification_service._send_email` (smtplib.SMTP, inline)
- `maskan_live_service._request_json` (sync HTTP)
- `gemini_service._generate_reasoning` (sync HTTP per property in recommendation loop)

### Error pattern

- Most services return `None`/`False`/`{}` on failure, log, never raise.
- Custom exceptions only in `services/sms/providers/` (provider-specific).
- `@log_execution` decorator on most service methods.
- No global exception handler middleware; routes catch and `jsonify(status=500)`.

---

## 6. Configuration & Infrastructure

### `app.py`

- SECRET_KEY from `SESSION_SECRET` env (`app.py:37`), fallback `"dev-secret-key-change-in-production"`.
- `ENABLE_CSRF=1` toggle at `app.py:43`.
- Security headers in `@app.after_request` at `app.py:133`.
- `instance/config.py` loaded if present; `test_config` override supported.

### `database.py`

- `SQLALCHEMY_DATABASE_URI` from `DATABASE_URL`; fallback `sqlite:///real_estate_crm.db`.
- `pool_recycle=300`, `pool_pre_ping=True`.

### `extensions.py`

- Cache, Limiter, Celery initialized here.
- `REDIS_URL` fallback `redis://localhost:6379/0` (silent default).
- `CACHE_TYPE` auto-detects Redis vs SimpleCache.

### `celery_app.py`

- Beat schedule controlled by env: `REMATCH_QUEUE_INTERVAL_MINUTES`, `MATCHING_INTERVAL_MINUTES`, `OVERDUE_TASK_INTERVAL_MINUTES`, `SMS_QUEUE_INTERVAL_SECONDS`, `SCORING_CRON_HOUR_UTC`, `SCORING_CRON_MINUTE_UTC`.
- Bound to `create_app()` at `celery_app.py:49`.

### Environment variables consumed (44 total)

Critical: `SESSION_SECRET`, `DATABASE_URL`, `ENABLE_CSRF`, `REDIS_URL`, `ADMIN_PASSWORD` (default `admin123`), `GEMINI_API_KEY`, `KIE_API_KEY`, `LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `SMS_PROVIDER`, `MASKAN_LIVE_*`, `MATCHER_*`, `SMTP_*`.

### Migrations

- 7 revision files in `migrations/versions/`.
- Two independent roots: `5b578ff077cb` (initial) and `20250825_add_indexes` (orphaned — never merged into linear chain).
- Linear chain from `5b578ff077cb`: `c4f9d2b8a1e6` → `d3e4f5a6b7c8` → `f1a2b3c4d5e6` → `a6d1c2e3f4a5` → `e8f9a0b1c2d3` (current HEAD).
- Note: `f1a2b3c4d5e6` timestamp (2026-02-12) older than `d3e4f5a6b7c8` (2026-02-17 16:20); revision ID ordering is authoritative but worth verifying.

### Tests

- 60+ test files in `tests/`.
- `conftest.py`: in-memory SQLite, app fixture, `client`, `db_setup`, sys.modules stubs for `vector_service` + `gemini_service`.
- Categories: smoke, routes, CRUD, forms, accessibility, CSRF contract, favorites, recommendations, matching, environment, SMS, providers, auth, startup, analytics, sync, copilot.

### CI (`.github/workflows/tests.yml`)

Two jobs:
1. **lint:** ruff, black --check, mypy (lenient subset: views, app, database, database_service, forms, init_db).
2. **tests:** pytest --cov with `--cov-fail-under=90`, `DATABASE_URL=sqlite:///:memory:`.

---

## 7. Cross-Cutting Concerns

### Critical security findings

1. **All public CRUD routes unauthenticated** (properties, agents, customers, deals, tasks, notifications). Anyone can read PII, create records, mutate others' records (IDOR).
2. **CSRF disabled by default.** `ENABLE_CSRF=0` ships. 5/6 forms skip CSRF.
3. **`.env` committed at repo root** with hardcoded `GEMINI_API_KEY`, `KIE_API_KEY`, `SESSION_SECRET='dev-secret'`, `FLASK_SECRET_KEY='dev-secret'`.
4. **`ADMIN_PASSWORD` default `admin123`** (env_loader fallback at `views/admin_environment.py:44,55,439`).
5. **Notification broadcast endpoint unauthenticated** — mass-message injection vector.
6. **`vector_api/vector_status` unauthenticated** — leaks persistence/infrastructure paths.
7. **`api_market_analysis` unauthenticated** — expensive AI call exposed.
8. **Module-level `app = create_app()` at `app.py:151`** runs init at import time — risky in WSGI re-import scenarios.

### Form/model drift summary

- Phone `Length(max=50)` vs DB `String(20)` (AgentForm, CustomerForm).
- Float→BigInteger implicit casts on money fields.
- ~30 model columns absent from `PropertyForm` (edit path can't update them).
- Free-form strings on enum-bound fields (status, priority, condition, category, listing_type).

### Performance hot paths (no index → slow on non-SQLite)

- `deals.{property_id,customer_id,agent_id}`
- `properties.agent_id`
- `tasks.agent_id`
- `property_matches.{property_id,customer_id,agent_id}`
- `agent_notifications.{agent_id,property_match_id}`

### Migration hazards

- Two migration roots (orphaned `20250825_add_indexes`).
- Soft-delete not enforced via SQLAlchemy event — every query must filter manually.
- No delete cascade on 1:N relationships → orphan rows possible after parent soft-delete.

### Observability

- `AIMetadata` + `ModelPerformanceMetric` tables track per-operation latency, token counts, success.
- `services/monitoring_service.py` aggregates system health, perf metrics, error summaries.
- `services/ai_model_analytics_service.py` records drift detection, A/B results.

---

## 8. Remediation Priorities

Sequenced by impact × reversibility.

### P0 — security lockout (block release)

1. **Lock all public CRUD behind auth.** Default `login_required` on every non-`/auth/*` blueprint. Use real session via `LoginManager` (currently absent).
2. **Enable CSRF by default** (`ENABLE_CSRF=1` shipped; flip all forms off `BaseNoCSRFForm`).
3. **Rotate + remove `.env` secrets.** Generate `.env.example`. Add `.env` to `.gitignore`. Purge from git history.

### P1 — data integrity

4. **Add missing FK indexes** via Alembic migration.
5. **Fix form/model drift:** phone `Length(max=20)`, `IntegerField` on money, `SelectField` choices on enums, cross-field budget validation.
6. **Audit soft-delete enforcement** — add SQLAlchemy event listener or query helper.

### P2 — code health

7. **Extract logic-in-routes** into services (priority targets: `properties.list`, `dashboard`, `rag_query`, `notifications.broadcast`).
8. **Resolve orphaned blueprints** — either register `analysis/analytics/rag` with auth + rate-limit, or delete.
9. **Move blocking IO off request path** — Celery tasks for email, recommendation reasoning, Maskan sync.
10. **Patch XSS sinks** in `modals/base_modal.html:53,70`.
11. **Merge orphaned migration** `20250825_add_indexes` into linear chain.

### P3 — polish

12. Externalize inline JS/CSS from templates.
13. Add `favicon.ico`.
14. Tighten mypy in CI to broader subset.

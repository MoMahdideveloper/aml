# Track A Security Route Matrix

Auto-generated from Flask `url_map`. **Expected auth is a starting hypothesis** —
confirm against `views/` and product policy before hardening.

Total non-static endpoints: **140**

| Methods | Path | Endpoint | Expected auth (verify) | CSRF | Sensitivity |
|---------|------|----------|------------------------|------|-------------|
| `GET` | `/` | `main.dashboard` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/` | `dashboard` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/admin/automations` | `automations.automations_dashboard` | admin_session (require_admin_auth) | n/a (safe method) | high |
| `GET` | `/admin/environment` | `admin_environment.environment` | admin_session (require_admin_auth) | n/a (safe method) | high |
| `POST` | `/admin/environment` | `admin_environment.create_environment_variable` | admin_session (require_admin_auth) | required when ENABLE_CSRF=1 | high |
| `DELETE` | `/admin/environment/<key>` | `admin_environment.delete_environment_variable` | admin_session (require_admin_auth) | required when ENABLE_CSRF=1 | high |
| `PUT` | `/admin/environment/<key>` | `admin_environment.update_environment_variable` | admin_session (require_admin_auth) | required when ENABLE_CSRF=1 | high |
| `GET` | `/admin/environment/<key>/details` | `admin_environment.get_environment_variable_details` | admin_session (require_admin_auth) | n/a (safe method) | high |
| `GET` | `/admin/environment/health-check` | `admin_environment.check_environment_health` | admin_session (require_admin_auth) | n/a (safe method) | high |
| `GET` | `/admin/environment/history` | `admin_environment.environment_history` | admin_session (require_admin_auth) | n/a (safe method) | high |
| `POST` | `/admin/environment/rollback` | `admin_environment.rollback_environment_changes` | admin_session (require_admin_auth) | required when ENABLE_CSRF=1 | high |
| `GET` | `/admin/environment/validation` | `admin_environment.get_validation_summary` | admin_session (require_admin_auth) | n/a (safe method) | high |
| `GET,POST` | `/admin/login` | `admin_environment.admin_login` | admin_session (require_admin_auth) | required when ENABLE_CSRF=1 | high |
| `GET` | `/admin/logout` | `admin_environment.admin_logout` | admin_session (require_admin_auth) | n/a (safe method) | high |
| `GET` | `/admin/notifications` | `notifications.admin_notifications_dashboard` | admin_session (require_admin_auth) | n/a (safe method) | high |
| `GET` | `/agents` | `agents.agents` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/agents` | `agents` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/agents/<int:agent_id>` | `agents.agent_dashboard` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/agents/<int:agent_id>/dashboard` | `agents.agent_dashboard` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST` | `/agents/<int:agent_id>/delete` | `agents.delete_agent` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | high |
| `POST` | `/agents/<int:agent_id>/edit` | `agents.edit_agent` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/agents/add` | `agents.add_agent` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/agents/add` | `add_agent` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/api/admin/notifications/broadcast` | `notifications.broadcast_system_notification` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/api/agents/<int:agent_id>` | `agents.get_agent_json` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `GET` | `/api/agents/<int:agent_id>/notifications` | `notifications.get_agent_notifications` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `POST` | `/api/agents/<int:agent_id>/notifications/<int:notification_id>/dismiss` | `notifications.dismiss_notification` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/api/agents/<int:agent_id>/notifications/<int:notification_id>/read` | `notifications.mark_notification_read` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/api/agents/<int:agent_id>/notifications/cleanup` | `notifications.cleanup_agent_notifications` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/api/agents/<int:agent_id>/notifications/mark-all-read` | `notifications.mark_all_notifications_read` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/api/agents/<int:agent_id>/notifications/summary` | `notifications.get_agent_notification_summary` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `GET` | `/api/automations/rules` | `automations.list_automation_rules` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `POST` | `/api/automations/rules` | `automations.create_automation_rule` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `PUT` | `/api/automations/rules/<int:rule_id>` | `automations.update_automation_rule` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/api/automations/test-trigger` | `automations.test_automation_trigger` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/api/customers/<int:customer_id>` | `customers.get_customer_json` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `POST` | `/api/customers/<int:customer_id>/matches/<int:property_id>/dismiss` | `main.dismiss_customer_match` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/api/deals/<int:deal_id>` | `deals.get_deal_json` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `GET` | `/api/market-analysis` | `main.api_market_analysis` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `GET` | `/api/matching/recent` | `main.matching_recent_feed` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `POST` | `/api/matching/run-now` | `main.matching_run_now` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/api/matching/status` | `main.matching_system_status` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `GET` | `/api/notifications/inbox` | `notifications.notifications_inbox` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `POST` | `/api/notifications/system` | `notifications.create_system_notification` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/api/opportunities/compose-message` | `main.api_opportunity_compose_message` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/api/opportunities/message-templates` | `main.api_opportunity_message_templates` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `POST` | `/api/opportunities/send-sms` | `main.api_opportunity_send_sms` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/api/properties/<int:property_id>/reveal-contact` | `properties.reveal_contact` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/api/properties/smart-search` | `properties.smart_search` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `GET` | `/api/tasks/<int:task_id>` | `tasks.get_task_json` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `GET` | `/api/v1/properties/<int:property_id>/edit-modal-html` | `properties.get_edit_modal_html` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `GET` | `/api/vector/status` | `vector_api.vector_status` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | medium |
| `GET,POST` | `/auth/login` | `auth.login` | public (login/register) or session (logout/profile writes) | required when ENABLE_CSRF=1 | medium |
| `GET` | `/auth/logout` | `auth.logout` | public (login/register) or session (logout/profile writes) | n/a (safe method) | low-medium |
| `GET` | `/auth/profile` | `auth.profile` | session optional / login for writes | n/a (safe method) | low-medium |
| `POST` | `/auth/profile/password` | `auth.change_password` | session optional / login for writes | required when ENABLE_CSRF=1 | medium |
| `POST` | `/auth/profile/update` | `auth.update_profile` | session optional / login for writes | required when ENABLE_CSRF=1 | medium |
| `GET,POST` | `/auth/register` | `auth.register` | public (login/register) or session (logout/profile writes) | required when ENABLE_CSRF=1 | medium |
| `GET` | `/auth/settings` | `auth.profile` | session optional / login for writes | n/a (safe method) | low-medium |
| `GET` | `/calculators` | `main.roi_calculator` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/calculators` | `roi_calculator` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/compare` | `main.property_compare` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/compare` | `property_compare` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/contracts` | `main.smart_contract` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/contracts` | `smart_contract` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/customers` | `customers.customers` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/customers` | `customers` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST` | `/customers/<int:customer_id>/briefs` | `main.create_customer_brief` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/customers/<int:customer_id>/briefs/<int:brief_id>/delete` | `main.delete_customer_brief` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | high |
| `POST` | `/customers/<int:customer_id>/briefs/<int:brief_id>/edit` | `main.edit_customer_brief` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/customers/<int:customer_id>/delete` | `customers.delete_customer` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | high |
| `POST` | `/customers/<int:customer_id>/edit` | `customers.edit_customer` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/customers/<int:customer_id>/match-preferences` | `main.update_match_preferences` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/customers/add` | `customers.add_customer` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/customers/add` | `add_customer` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/dashboard` | `main.dashboard` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/deals` | `deals.deals` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/deals` | `deals` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST` | `/deals/<int:deal_id>/delete` | `deals.delete_deal` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | high |
| `POST` | `/deals/<int:deal_id>/note` | `deals.add_deal_note` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/deals/<int:deal_id>/update` | `deals.update_deal` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/deals/<int:deal_id>/update` | `update_deal` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/deals/add` | `deals.add_deal` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/deals/add` | `add_deal` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/get_customer_recommendations/<int:customer_id>` | `main.get_customer_recommendations` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/get_customer_recommendations/<int:customer_id>` | `get_customer_recommendations` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/healthz` | `healthz` | public | n/a (safe method) | low-medium |
| `GET` | `/kiosk` | `main.open_house_kiosk` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/kiosk` | `open_house_kiosk` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/kiosk/<int:property_id>` | `main.open_house_kiosk_property` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST` | `/kiosk/<int:property_id>/checkin` | `main.open_house_checkin` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/market` | `main.market_analysis` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/market` | `market_analysis` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/market-analysis` | `main.market_analysis` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/messaging` | `main.messaging` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/messaging` | `messaging` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/messaging/<int:customer_id>` | `main.messaging` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST` | `/messaging/<int:customer_id>/send` | `main.messaging_send` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/open-house` | `main.open_house_kiosk` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/properties` | `properties.properties` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/properties` | `properties` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/properties/<int:property_id>` | `properties.view_property` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST,PUT` | `/properties/<int:property_id>` | `properties.update_property` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/properties/<int:property_id>/ai-history` | `properties.get_property_ai_history` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST` | `/properties/<int:property_id>/delete` | `properties.delete_property` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | high |
| `GET` | `/properties/<int:property_id>/detail` | `properties.property_detail` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/properties/<int:property_id>/edit` | `properties.edit_property` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET,POST` | `/properties/<int:property_id>/media` | `properties.property_media` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/properties/<int:property_id>/media/<int:image_id>/delete` | `properties.delete_property_image` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | high |
| `POST` | `/properties/<int:property_id>/media/<int:image_id>/primary` | `properties.set_primary_image` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/properties/<int:property_id>/media/upload` | `properties.upload_property_media` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET,POST` | `/properties/<int:property_id>/schedule-viewing` | `properties.schedule_viewing` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/properties/<int:property_id>/share` | `properties.share_property` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/properties/<int:property_id>/share` | `properties.share_property` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST` | `/properties/add` | `properties.add_property` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/properties/add` | `add_property` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `DELETE` | `/properties/ai-history/<int:history_id>` | `properties.delete_property_ai_history` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | high |
| `POST` | `/properties/extract-from-image` | `properties.extract_property_from_image` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/properties/extract-from-text` | `properties.extract_property_from_text` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/properties/map` | `properties.map_view` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST` | `/properties/map/geocode` | `properties.geocode_missing_coords` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/properties/map/persist-approx` | `properties.persist_approx_coords` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/readyz` | `readyz` | public | n/a (safe method) | low-medium |
| `GET` | `/recommendations` | `main.recommendations` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/recommendations` | `recommendations` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/roi` | `main.roi_calculator` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/settings` | `settings` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/smart-contract` | `main.smart_contract` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/sms` | `main.sms_broadcast` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/sms` | `sms_broadcast` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/sms-broadcast` | `main.sms_broadcast` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST` | `/sms/send` | `main.sms_send` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `GET` | `/tasks` | `tasks.tasks` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `GET` | `/tasks` | `tasks` | VERIFY: often public-read in current code; confirm product intent | n/a (safe method) | low-medium |
| `POST` | `/tasks/<int:task_id>/complete` | `tasks.complete_task` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/tasks/<int:task_id>/complete` | `complete_task` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/tasks/<int:task_id>/delete` | `tasks.delete_task` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | high |
| `POST` | `/tasks/<int:task_id>/edit` | `tasks.edit_task` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/tasks/add` | `tasks.add_task` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |
| `POST` | `/tasks/add` | `add_task` | VERIFY: often public-read in current code; confirm product intent | required when ENABLE_CSRF=1 | medium |

## Access model (from code + Phase 3 tests, 2026-07-10)

**Product model: global staff CRM (single office dataset), not multi-tenant ownership.**

| Identity | Gate | Data scope |
|----------|------|------------|
| Anonymous | `AUTH_DEFAULT_DENY_ENABLED=1` → 302 login / 401 API | None |
| Authenticated user (`session['user_id']`) | Default-deny middleware | **All** customers, properties, agents, deals, tasks (global) |
| Role `agent` / `viewer` | Stored on User; **not enforced** on list/detail/mutate routes today | Same as any authenticated user |
| Admin (`session['admin_authenticated']`) | `require_admin_auth` + middleware admin path | `/admin/*` environment tools; separate from User login |

Session keys: `user_id`, `user_role`, `user_name` (`views/auth.py`); admin uses `admin_authenticated` / `admin_user`.

**IDOR implication:** Cross-user access to the same customer/deal IDs is **expected** under this model. Contract tests in `tests/test_authz_deny_first.py` lock that in. If product later needs per-agent ownership, invert those tests and add repository-level scopes — do not invent tenancy without a product decision.

Pytest: `conftest.py` sets `AUTH_DEFAULT_DENY_ENABLED=0` for legacy open-route tests; security tests rebuild the app with deny on.

CSRF: enabled when `ENABLE_CSRF=1` or production default (`app.py`).

## Findings seed (for security agent)

| ID | Severity | Finding |
|----|----------|---------|
| F1 | mitigated (auth) | Default-deny middleware implemented; enable with `AUTH_DEFAULT_DENY_ENABLED=1` |
| F2 | accepted risk (documented) | No object-level isolation among staff — intentional global CRM; admin still isolated |
| F3 | medium | Dual endpoint aliases (blueprint + bare) increase CSRF/test surface |
| F4 | medium | Admin JSON/API routes need same controls as HTML — partial via middleware admin paths |
| F5 | high | Login/register/admin login lack rate limits; Flask-Limiter not wired into `create_app` (see `artifacts/SECURITY_PHASE2_FINDINGS.md`) |
| F6 | low | `user_role` (agent/viewer) is stored but not enforced on CRM routes |

Regenerate: `python scripts/export_security_route_matrix.py`


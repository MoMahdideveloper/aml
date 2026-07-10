# Follow-up automation — operator guide

## Access
Admin UI: `/admin/automations` (admin password session).

## Safety
1. **Seed disabled templates** — never enables rules.
2. **Dry-run** a rule against recent outbox events (no writes).
3. **Toggle** enable only after review.
4. **Kill switch** stops new actions; outbox retains events.
5. **Process outbox** drains pending events.

## Default templates (disabled)
- New customer follow-up
- Viewing preparation
- Negotiation follow-up
- Stale deal reminder
- Overdue task reminder
- High-value stalled escalation
- Close-deal cleanup

## Flags
- `ENABLE_AUTOMATION=0` — env kill switch
- DB `automation_settings.global_enabled` — runtime kill switch

## Scanners
Admin buttons emit scan events then process outbox. Safe to re-run (idempotent actions).

## No email/SMS in v1
In-app tasks + AgentNotification only.

# Follow-up automation contract (Track A)

## Events (canonical emission)
| Event type | Source |
|------------|--------|
| `customer.created` | `database_service.add_customer` |
| `deal.created` | `database_service.add_deal` |
| `deal.stage_changed` | `database_service.update_deal` (status change) |
| `deal.closed` | stage → closed_won / closed_lost |
| `task.completed` | `database_service.complete_task` / update status completed |
| `task.cancelled` | task status → cancelled |
| `scan.inactive_deals` | scanner |
| `scan.overdue_tasks` | scanner |
| `scan.high_value_stalled` | scanner |

Envelope: event_id, event_type, aggregate_type, aggregate_id, actor_id, occurred_at, correlation_id, changed_fields (names only), schema_version, context_json (allowlisted keys only).

## Conditions (allowlisted)
`event_type`, `stage`, `stage_in`, `min_offer_amount`, `max_offer_amount`, `inactive_days_min`, `task_overdue`, `entity_type`, `assignee_present`

Operators are implicit on field keys only — no expressions/SQL/code.

## Actions (allowlisted)
| type | params |
|------|--------|
| `create_task` | `title_key`, `due_days`, `priority`, `assignee` (`deal_agent`\|`context_agent`) |
| `notify` | `title_key`, `message_key`, `priority` |
| `cancel_automation_tasks` | `match_title_keys` (optional list) |
| `escalate` | `title_key`, `message_key` (notify all admin users as manager proxy) |

## Title keys (no free Jinja)
`contact_new_customer`, `prepare_viewing`, `negotiation_followup`, `stale_deal_reminder`, `overdue_task_reminder`, `high_value_stalled`, `escalation`

## Idempotency
`rule_id + event_id + action_type` unique on successful run. Cooldown per rule+aggregate.

## Kill switch
`ENABLE_AUTOMATION=0` or runtime `AutomationSettings.global_enabled=False`.

## Default templates
Seeded **disabled**. Migration never enables rules.

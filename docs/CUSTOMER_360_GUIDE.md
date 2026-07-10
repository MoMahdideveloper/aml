# Customer 360 & activity timeline

## Overview
One chronological activity view per customer combining:
- **Manual interactions** (notes, calls, emails, meetings) stored in `customer_interactions`
- **Generated events** (deal created/stage changes, follow-up tasks) projected read-only from source tables

## Taxonomy
| Type | Source | Editable |
|------|--------|----------|
| note, call, email, meeting, other | manual | yes |
| system (deal events) | deals / stage history | no |
| task | tasks linked to interactions | no |

## Permissions
Authenticated CRM staff (session). Global staff model. Soft-deleted customers/interactions hidden.

## Privacy
- Note **bodies excluded from global search**
- Search may use name, email, phone, optional subject (not body)
- Audit logs store field **names only**, never body/PII values
- Templates escape user content (`body_html` via `html.escape`)

## Follow-up tasks
Optional when `follow_up_at` is set. Idempotent: one task per interaction (`source_entity_type=interaction`, `source_entity_id`).

## Pagination
Cursor: `occurred_at|id` descending. Default page 25, max 100. First page does not load unbounded history.

## Timezone
Naive UTC timestamps; periods half-open `[start, end)`.

## Automation
`interaction.created` outbox event (safe context). Template `tpl_call_no_answer` (disabled by default).

## Explicit non-goals
- mailbox / calendar sync
- call recording
- message delivery tracking
- note-body global search

## Routes
- `GET /customers/<id>` — Customer 360
- `POST /customers/<id>/interactions` — create
- `POST .../edit` · `POST .../delete`

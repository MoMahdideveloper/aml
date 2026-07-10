# Sales reports — operator guide

## Open
Sidebar **Sales report** or `/reports/sales` (agent/admin, logged in).

## Filters
- **days** — trailing period (default 30)
- **start/end** — ISO dates; end exclusive
- **agent_id** — optional single agent

Comparison uses the immediately preceding equal-length period (non-overlapping).

## Metrics
See `docs/SALES_METRIC_CONTRACT.md` for formulas.  
Weighted forecast = open value × stage probability (transparent table, not ML).

## Export
**Export CSV** uses the same filters/service. Formula-injection neutralized. Max rows bounded.

## Snapshot
**Snapshot current forecast** stores weighted/open totals for later accuracy (no deal PII). Accuracy only after period closes.

## Flag
`ENABLE_SALES_REPORTS=0` hides nav and 404s routes.

## Stage history
Create/update deal status writes `deal_stage_history`. Legacy deals may only have baseline events — conversion metrics exclude baselines.

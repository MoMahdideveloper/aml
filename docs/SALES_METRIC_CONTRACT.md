# Sales reporting metric contract (Track A)

## Data readiness (Deal / Agent / Task)

| Metric | Status | Notes |
|--------|--------|--------|
| Current pipeline value | **Direct** | Sum `offer_amount` for non-deleted open stages |
| Weighted forecast | **Direct** | Open value × stage probability (config) |
| Won/lost value | **Direct** | Terminal stages `closed_won` / `closed_lost` |
| Win rate | **Direct** | won_count / (won+lost) in period by `updated_at` when terminal |
| Average deal size | **Direct** | won_value / won_count |
| Stage conversion | **Derivable** after history | Requires `deal_stage_history` observed transitions |
| Time in stage | **Derivable** after history | Between consecutive history rows |
| Sales-cycle duration | **Derivable** | History first→won, else proxy `updated_at - created_at` for won |
| Agent performance | **Direct** | Filter by `agent_id`; reassignment uses **current** agent |
| Forecast accuracy | **Derivable** | After `forecast_snapshots` + closed period |

**Not inventable:** multi-step historical transitions for legacy deals. Backfill is **baseline only**.

## Canonical stages
Open: `prospecting`, `contact_made`, `property_shown`, `offer_submitted`, `negotiation`  
Won: `closed_won` · Lost: `closed_lost`  
Normalization: same aliases as `views/deals.py` / `services/deal_pipeline.py`.

## Formulas
- **pipeline_value** = Σ offer_amount of open, non-deleted deals (optional period filter: created_at &lt; end)
- **weighted_forecast** = Σ (open offer_amount × P(stage))
- **won_value / lost_value** = Σ offer_amount for deals that **became** terminal in period (prefer history `changed_at`; else `updated_at` in period and current status terminal)
- **win_rate** = won_count / (won_count + lost_count); if denom=0 → `null` (neutral)
- **avg_deal_size** = won_value / won_count; denom=0 → `null`
- **sales_cycle_days** = mean over won deals of (won_at − created_at) in days; missing → exclude from mean
- **stage_conversion** = exits to “forward” next stage / entries (observed history only; baseline excluded)
- **period comparison** = current vs prior equal-length window; ends exclusive; no overlapping days

## Inclusion rules
- Soft-deleted deals **excluded** always
- Currency: integer toman (BigInteger); display with grouping; Decimal arithmetic in service
- Timezone: naive UTC timestamps (`_utcnow_naive`)
- Period: `[start, end)` half-open
- Cancelled: treat as deleted if `is_deleted`; no separate cancel status
- Reassigned agent: metrics use **current** `agent_id`
- Reopen (lost/won → open): new open pipeline; history records transition; accuracy uses snapshots only
- Missing offer_amount: treat as 0

## Stage probabilities (config source: `services/deal_pipeline.py`)
| Stage | P | Rationale |
|-------|---|-----------|
| prospecting | 0.10 | Early lead |
| contact_made | 0.20 | Engaged |
| property_shown | 0.35 | Serious interest |
| offer_submitted | 0.50 | Formal offer |
| negotiation | 0.70 | Late stage |
| closed_won | 1.00 | Terminal |
| closed_lost | 0.00 | Terminal |

Updates require code/config change and audit note in this file. Historical reports use **current** probability table (not snapshotted per stage) unless a forecast snapshot row exists.

## Permissions
Authenticated CRM staff (`agent`/`admin` session). Global read model (same as deals list).  
`ENABLE_SALES_REPORTS` flag (default on).

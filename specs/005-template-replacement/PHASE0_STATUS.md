# Phase 0 Status — Decisions locked & kickoff

**Date**: 2026-07-09  
**Decisions**:
- Brand: **Platinum Heritage**
- Scope: **P0 + P1**
- Market Analysis / Agent Dashboard pages: **later**
- Stitch: **re-apply design system via MCP** (preferred)

## Stitch MCP

| Action | Result |
|--------|--------|
| `get_project` / `list_screens` / `list_design_systems` / `get_screen` | OK (read) |
| Design system present | `assets/1dee9814aeab494b99629a9fe04852bd` — **Platinum Heritage** already on project |
| `apply_design_system` | **FAILED** — OAuth write credential missing |
| `edit_screens` | **FAILED** — same OAuth write error |

Read tools work; **mutation tools need a fresh Stitch OAuth login** in the MCP / Google account session.

### What you need to do for true “re-apply in Stitch”

1. Re-authenticate Stitch MCP (Google OAuth for the account that owns project `1843282501813018645`).
2. Re-run apply for batches under `tmp/stitch_apply_batches/batch_*.json` against asset `1dee9814aeab494b99629a9fe04852bd`.
3. Optional brand pass via `edit_screens` with prompt: unify all chrome to “Platinum Heritage”, Deep Blue `#2A3A4B`, IBM Plex Sans.
4. Re-run `python tmp/sync_p0p1_from_stitch.py` to refresh local HTML.

Until write auth is restored, we use:
- Existing project theme (already Platinum Heritage tokens)
- Local re-download of current screen HTML (read-only)
- Flask shell brand lock (done)

## Canonical map

See `CANONICAL_SCREENS.json` — 28 P0+P1 screens frozen (desktop, mobile, modals).

## Flask changes done (Phase 0 / shell)

- `templates/components/_sidebar.html` → brand Platinum Heritage, correct active endpoints, Map + Settings links
- `templates/components/_mobile_header.html` → brand + auth profile/logout links
- `templates/base.html` → default title Platinum Heritage

## Local HTML sync

`python tmp/sync_p0p1_from_stitch.py` → **28/28 OK** into `stitch_kpi_performance_dashboard/`  
(Task modal uses folder `task_management_modal/` so it does not overwrite tasks desktop.)

## Phase 1–2 progress (2026-07-09 continued)

### Done
- Shell: `base.html` PH Tailwind tokens, sidebar + mobile nav, brand lock
- Dashboard: fully dynamic stats / activity / tasks / insights (no demo schedule)
- P0 pages brand-aligned (properties, agents, customers, deals, tasks, property detail)
- P1: map rebuilt (Leaflet + `properties_json`), settings PH + user fields, auth brand
- Route smoke: all P0+P1 GETs return **200**
- Fixes: tasks `now`, deals/customers `agents_list`, mobile menu JS

### Modal + cleanup pass (continued)
- PH modals: share, deal view, email compose, viewing schedule, task edit, base_modal shell
- Property edit modal chrome converted to PH overlay (form fields retained)
- Recommendations tips + create-deal modals PH; JS no longer depends on Bootstrap Modal
- `PHModal` helpers in `app-core.js` (show/hide, Escape, backdrop)
- Archived 12 orphan templates → `templates/_archive/20260709-orphans/`

### Modal field restyle + view modals (continued)
- property_edit: 0 form-control/form-select left; PH inputs + tab switcher
- property_view: full PH shell; JS IDs preserved; bootstrap Modal fallback removed
- customer_view / customer_edit / task_view / meeting_schedule / agent_edit → PH
- crud-utils.showModal supports PH `data-modal` overlays without Bootstrap

### JS + enhanced modal pass
- Archived `property_view_modal_enhanced.html` (unused)
- `PHModal` helper hardened (string ids, bootstrap cleanup)
- recommendations.js / dual-view-handler / button-fixes / property-modal-system / crud-utils dynamic modals → PH open/close
- confirmDelete + createDynamicModal use PH overlays

### Wiring + polish pass
- Properties inventory: Quick view / Full page / delete wired; includes view+share modals + JS
- Property detail: fixed broken stat/detail grids; condition field shows real condition
- analysis.js report + suggestion modals → PH overlays

### Optional leftovers
- analysis.js progress/spinner modals may still use Bootstrap in places
- Optional Stitch OAuth re-apply
- Hard-delete `_archive/` after soak
- Screenshot parity pass vs Stitch

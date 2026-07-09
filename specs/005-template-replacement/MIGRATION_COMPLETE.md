# Platinum Heritage UI Migration — Complete

**Branch**: `005-template-replacement`  
**Stitch project**: `1843282501813018645`  
**Brand**: Platinum Heritage  
**Scope delivered**: P0 + P1 pages, modals, JS openers, list-page actions  

## Delivered

### Shell
- `base.html` — PH Tailwind tokens, IBM Plex Sans, Material Symbols
- Sidebar + mobile header brand lock, Map + Settings nav
- `PHModal` helper (`static/js/app-core.js`)

### Dynamic pages
| Route | Status |
|-------|--------|
| Dashboard `/` | Dynamic stats, activity, tasks, insights |
| Properties | Filters, grid, Quick view, Full page, delete |
| Property detail | Fixed grids, PH stats |
| Agents | Edit (API + modal), delete |
| Customers | Profile modal (API), delete, email |
| Deals | Kanban, deal detail modal (API), delete |
| Tasks | List + add modal (`now` fixed) |
| Recommendations | PH tips/create-deal; export modal |
| Map | Leaflet + live coordinates |
| Settings / Auth | PH restyle |

### Modals
All core modals under `templates/modals/` converted to PH Tailwind overlays (view/edit/share/deal/email/task/meeting/agent/customer).

### Cleanup
- Orphans archived under `templates/_archive/20260709-orphans/`
- Stitch P0+P1 HTML synced under `stitch_kpi_performance_dashboard/`
- Canonical map: `CANONICAL_SCREENS.json`

## Stitch write re-apply
**Blocked**: MCP write (`apply_design_system` / `edit_screens`) requires OAuth re-auth.  
Read/sync already done. Project design system is already Platinum Heritage.

To re-apply after re-auth:
1. Re-login Stitch MCP (Google account owning the project)
2. Apply batches in `tmp/stitch_apply_batches/`
3. `python tmp/sync_p0p1_from_stitch.py`

## Verify locally
```bash
python main.py
# Open http://127.0.0.1:5000
# Click: Dashboard, Properties → Quick view, Agents → Edit, Customers → View Profile, Deals → card
```

## Final action wiring (follow-up)
- Agents: edit modal + delete
- Customers: profile modal + delete + mailto
- Deals: detail modal + delete
- Properties: quick view + full page + delete
- Tasks: complete + delete actions on rows
- Agent form: phone required + bio field aligned with `AgentForm`

## Quality pass
- 404/500 pages: Platinum Heritage branding + tokens
- Flash toasts: PH surface/error colors
- Property add form: `sale_price`, `square_feet`, `listing_type`, agent select (matches `PropertyForm`)
- TaskForm: optional description + agent (UI can leave unassigned)
- Modal openers: `data-open-modal` on all list pages

## Verify
```bash
$env:PYTHONPATH='.'; python tmp/verify_ui_migration.py
$env:PYTHONPATH='.'; python tmp/audit_url_for.py
$env:PYTHONPATH='.'; python -m pytest tests/test_platinum_heritage_ui.py -q
```

## Optional later
- Hard-delete `_archive/`
- Visual QA vs Stitch screenshots
- Stitch OAuth write re-apply (MCP write still needs re-login)
- Market Analysis / Agent personal dashboard routes (deferred by plan)

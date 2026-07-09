# Full UI Migration Plan: Stitch Consistency → Flask Dynamic Pages

**Branch**: `005-template-replacement`  
**Stitch project**: `1843282501813018645` (KPI Performance Dashboard / Platinum Heritage)  
**Date**: 2026-07-09  
**Status**: Ready for approval → execute by phase  

---

## 1. Goal

Make **every product UI page** in this CRM:

1. **Visually consistent** with the Stitch **Platinum Heritage** design system  
2. Available for **desktop and mobile** (responsive shell + mobile-specific layouts where Stitch has them)  
3. **Integrated into Flask** as Jinja2 templates with real DB data  
4. **Old / inconsistent pages removed** (or archived once nothing references them)  
5. Fully **dynamic** (no hard-coded demo names, prices, or agent profiles)

---

## 2. Current state (what we already have)

| Area | Status |
|------|--------|
| Stitch project | 56 screens (28 desktop, 24 mobile, 4 misc) |
| Local Stitch export | `stitch_kpi_performance_dashboard/` (~107 HTML files) |
| Design tokens | `static/css/stitch.css` (Platinum Heritage) + theme on Stitch project |
| Shell | `templates/base.html` + `components/_sidebar.html`, `_mobile_header.html`, `_flash_messages.html` |
| Partially dynamic pages | `dashboard.html`, `properties.html`, `agents.html`, `customers.html`, `deals.html`, `tasks.html`, `settings_preferences.html` |
| Still inconsistent / partial | brand name in sidebar (“Real Estate CRM”), auth pages, property detail, map, recommendations, admin, many modals |
| Old templates | Many already moved to `templates/_archive/`; some legacy standalone HTML remain in export folders |
| Specs | `specs/005-template-replacement/*` exists but is incomplete / generic |

**Known consistency problems (from prior audit + live code):**

- Multiple brand names historically (Luxe Estate, Heritage Elite, Stitch KPI, etc.)
- Some pages extend `base.html`; others were standalone full documents
- Mobile often = separate Stitch HTML, not one responsive system
- Sidebar endpoints may not match blueprint endpoint names
- Hard-coded sample content still mixed with Jinja loops on several pages

---

## 3. Design system (single source of truth)

**Brand name (locked):** **Platinum Heritage** (optional product name: EstateSync CRM under that shell)

| Token | Value |
|-------|--------|
| Primary | `#142435` / container `#2A3A4B` |
| Secondary / platinum | `#C0C0C0` (borders, dividers) |
| Background surface | `#F7F9FF` (code tokens); cream `#F4F2E5` only if design.md gallery pages need it |
| Text | `#111D27` / `#1B2631` |
| Cards | `#FFFFFF` |
| Font | IBM Plex Sans (all roles) |
| Radius | 4px controls, 8px cards |
| Shadow | `0 8px 30px rgba(27, 38, 49, 0.06)` hover only |
| Grid | max-width 1280px, 24px gutters, 8px spacing scale |

**Rules every page must follow:**

1. Extends `templates/base.html` (except pure auth / kiosk full-bleed layouts that still import the same tokens)  
2. No page-local brand rename  
3. No page-local primary color overrides  
4. All assets via `url_for('static', ...)`  
5. All lists/tables driven by route context, with empty states  
6. Forms keep field names expected by Flask-WTF / existing POST handlers  
7. Material Symbols or Font Awesome — pick **one icon set for chrome** (recommend Material Symbols to match Stitch; keep FA only if needed for legacy JS)

---

## 4. Architecture decisions (recommended)

### 4.1 One shell, not two apps

```
templates/
  base.html                 # desktop sidebar + mobile top bar
  components/               # shared chrome + cards + empty states
  partials/                 # header/footer only if needed beyond components
  pages/                    # optional later; keep flat names for route stability first
  modals/                   # fragment templates for AJAX modals
  mobile/                   # ONLY when layout is truly different (rare)
```

**Do not** ship parallel `*_mobile.html` routes for every page.  
Instead:

- **Default**: one responsive template using Tailwind breakpoints (`lg:` sidebar, mobile header already in base).  
- **Exception**: when Stitch mobile layout is structurally different (e.g. bottom sheets, mobile pipeline cards), extract a **content partial** and optionally include a mobile block:

```jinja2
{% extends "base.html" %}
{% block content %}
  <div class="lg:hidden">{% include "partials/deals_pipeline_mobile_body.html" %}</div>
  <div class="hidden lg:block">{% include "partials/deals_pipeline_desktop_body.html" %}</div>
{% endblock %}
```

Same route, same data context, two layout bodies if needed.

### 4.2 Dynamic binding pattern

```python
# views/*.py — keep existing service calls; only change template path if needed
return render_template(
    "properties.html",
    properties=properties,
    pagination=pagination,
    ...
)
```

```jinja2
{% for p in properties %}
  <a href="{{ url_for('properties.property_detail', property_id=p.id) }}">
    {{ p.title }} · {{ p.price }}
  </a>
{% else %}
  {% include "components/_empty_state.html" %}
{% endfor %}
```

### 4.3 Stitch HTML conversion recipe (repeatable)

For each screen:

1. Open canonical HTML from `stitch_kpi_performance_dashboard/<screen>/code.html` (or re-download via Stitch MCP if newer)  
2. Strip outer `<html>/<head>/<body>` and duplicate sidebars/nav  
3. Keep page content only → paste into `{% block content %}`  
4. Replace demo text with Jinja variables from the existing route  
5. Wire buttons to existing endpoints / modals / `url_for`  
6. Ensure CSRF on POST forms  
7. Smoke-test desktop 1280+ and mobile 390  

### 4.4 Delete vs archive

- **During migration**: move superseded files to `templates/_archive/YYYYMMDD/`  
- **After full green tests**: delete archive in a cleanup PR (optional)  
- **Never delete** templates still referenced by `render_template(...)` without updating the route first  

---

## 5. Screen inventory → product mapping

### 5.1 In scope (product CRM) — implement & wire

| Priority | Product page | Flask route(s) | Stitch desktop | Stitch mobile | Current template | Action |
|----------|--------------|----------------|----------------|---------------|------------------|--------|
| P0 | Dashboard | `main.index` `/` | Dashboard Overview `37656f67…` | Dashboard Overview Mobile `69a6fa40…` / `19ddb379…` | `dashboard.html` | Finalize dynamic; remove leftover demo schedule/insights or drive from API |
| P0 | Properties list | `properties.properties` | Property Inventory `014e9d15…` | Property Inventory Mobile `653abd98…` | `properties.html` | Align to Stitch layout; keep search/pagination |
| P0 | Property detail | `properties.property_detail` | Property Detail Villa `3f39f30c…` | Property Detail Mobile `389045ac…` / `d0653c31…` | `property_details.html` | Full Stitch convert + dynamic fields |
| P0 | Agents | `agents` `/agents` | Agent Management `c95b5a8d…` | Agent Management Mobile `a5f634f6…` | `agents.html` | Dynamic agents list + edit modal |
| P0 | Customers | `customers` `/customers` | Clients Management `3a97d783…` | Clients Mobile `2cb4425a…` | `customers.html` | Dynamic clients + modals |
| P0 | Deals | `deals` `/deals` | Deals Pipeline `2c42cf67…` | Deals Pipeline Mobile `ae2d2a74…` | `deals.html` | Kanban from `pipeline_stats` + deals |
| P0 | Tasks | `tasks` `/tasks` | Tasks Management `cd9cb221…` | Tasks Mobile `47f2e1c3…` | `tasks.html` | Dynamic tasks + agents |
| P1 | Settings | settings route (add if missing) | Settings Preferences `95065fea…` | Settings Mobile `1d590d53…` | `settings_preferences.html` | Wire real prefs / user profile |
| P1 | AI Recommendations | `main.recommendations` | AI Smart Property Matcher `157fc6ef…` | (use responsive) | `recommendations.html` | Restyle to PH; keep Gemini flow |
| P1 | Map | `properties.map_view` | Property Location Map / Immersive Street View | same mobile variants | `map_view.html` | Restyle chrome; keep map JS |
| P1 | Auth login/register | `auth.login` / `register` | *(no dedicated Stitch — restyle)* | responsive | `auth_*.html` | Apply PH tokens; standalone layout OK |
| P1 | Agent dashboard | optional `/agents/<id>` or profile | Agent Dashboard Sterling `184bb87c…` | Agent Dashboard Mobile `58586706…` | none | New route **or** fold into agent detail modal |
| P2 | Market analysis | `/market` or dashboard section | Market Analysis `ddd4b069…` | Market Analysis Mobile `2a79d3a5…` | API only today | New page using `api_market_analysis` data |
| P2 | Notifications | admin notifications | System Alerts / Notification Settings | — | `admin_notifications.html` | Restyle to PH |
| P2 | Admin env / automations | `/admin/*` | — | — | admin templates | Restyle chrome only (keep functional forms) |

### 5.2 Fragments / modals — convert as shared components

| Stitch screen | Target template | Data source |
|---------------|-----------------|-------------|
| Property share bottom sheet | `modals/property_share_modal.html` | property |
| Deal dossier & stage edit | `modals/deal_view_modal.html` | deal |
| VIP client profile edit | `modals/customer_edit_modal.html` / view | customer |
| VIP email composer | `modals/email_compose_modal.html` | customer + property |
| Task management modal | `modals/task_edit_modal.html` / view | task |
| Luxury listing price edit | `modals/property_edit_modal.html` | property |
| Private viewing scheduler | `modals/viewing_schedule_modal.html` | property + agents |
| Meeting schedule | `modals/meeting_schedule_modal.html` | customer |
| Contact agent form (mobile) | form partial on property detail | agents |

### 5.3 Optional / later (do not block MVP)

| Screen | Why later |
|--------|-----------|
| Commission & Revenue Analytics Hub | Needs metrics service not fully exposed as page |
| Open House Lead Capture Kiosk | Kiosk mode, separate UX |
| Smart Contract & Lease Generator | Likely not backed by models yet |
| List Your Property multi-step wizard | Overlaps property create form |
| Upload Property Media | Overlaps existing upload endpoints |
| Executive Comparison Matrix | Overlaps recommendations/compare |
| Client Messaging Portal | Needs messaging backend |
| Photo gallery / amenities / description subpages | Can be tabs on property detail first |
| Three.js / Shader | Experiments — **exclude** |
| DESIGN.md uploads | Not UI pages — **exclude** |
| Animated Dashboard duplicate | Keep one dashboard only |

---

## 6. Consistency pass on Stitch (before coding)

Use Stitch MCP on project `1843282501813018645`:

### Phase A — Audit (read-only)

1. `list_screens` + group by product domain  
2. Pick **canonical** desktop + mobile per domain (discard older duplicates)  
3. For each canonical pair, visual check:  
   - same primary/sidebar brand  
   - same nav order  
   - IBM Plex Sans  
   - card radius / border platinum style  
4. Document winners in a mapping table (section 5)  

### Phase B — Fix in Stitch (only if still generating from Stitch)

If screens diverge:

1. Ensure design system **Platinum Heritage** is applied via `apply_design_system` to selected screen instances  
2. `edit_screens` prompt: *“Unify navigation labels, brand name Platinum Heritage, sidebar icons, and header height with Dashboard Overview. Keep layout.”*  
3. Re-export HTML into `stitch_kpi_performance_dashboard/` via existing `sync_stitch.py` or MCP download  

**Canonical device strategy:** DESKTOP primary; MOBILE as companion layouts only.

### Phase C — Freeze

Lock screen IDs used for conversion so agents don’t chase regenerations mid-migration.

---

## 7. Implementation phases (execute in order)

### Phase 0 — Prep (½ day)

- [ ] Re-sync Stitch → `stitch_kpi_performance_dashboard/` if screens updated today  
- [ ] Fix `components/_sidebar.html` endpoint names to match blueprints (`main.index`, `properties.properties`, `agents.agents`, etc.)  
- [ ] Brand lock: sidebar + mobile header → **Platinum Heritage**  
- [ ] Single Tailwind config / token map in `base.html` or `stitch.css` (no per-page CDN config drift)  
- [ ] Inventory all `render_template(...)` call sites → spreadsheet of template → route  
- [ ] Add `tests/test_template_routes_smoke.py`: every page route returns 200 and extends base (or allowed auth layout)

### Phase 1 — Shell & shared components (1 day)

- [ ] Harden `base.html` (tokens, fonts, Material Symbols, flash, sidebar, mobile header, content block)  
- [ ] Components: `_stat_card`, `_empty_state`, `_card_list_item`, `_action_button`, flash, sidebar, mobile header  
- [ ] Standard page header partial (title, subtitle, primary CTA)  
- [ ] Delete/stop using duplicate partials: `_ph_*` vs `_sidebar` — **keep one set** under `components/`  
- [ ] JS: one `app-core.js` for sidebar toggle / mobile menu  

### Phase 2 — P0 pages (dynamic conversion) (3–4 days)

Order (dependency + traffic):

1. **Dashboard** — real stats already; remove fake schedule/insights or load from services  
2. **Properties list** — pagination/search preserved  
3. **Property detail** — largest Stitch surface; fields from `property_data` dict  
4. **Deals pipeline** — stage columns from `pipeline_stats`  
5. **Customers**  
6. **Agents**  
7. **Tasks**  

For each page:

- Convert HTML → Jinja  
- Wire CRUD buttons to existing POST routes / modals  
- Empty states  
- Desktop + mobile viewport check  
- Commit per page  

### Phase 3 — Modals & interactions (1–2 days)

- Align all `templates/modals/*` to PH chrome  
- Ensure property edit/view, deal, customer, task, share, email, viewing modals load via existing AJAX endpoints  
- CSRF + field name regression tests  

### Phase 4 — P1 pages (1–2 days)

- Recommendations (AI matcher visual)  
- Map view chrome  
- Settings + notification prefs  
- Auth login/register PH restyle  

### Phase 5 — P2 / new routes (optional 2–3 days)

Only if product needs them:

- Market analysis page (`/analysis` or `/market`)  
- Agent personal dashboard  
- Commission analytics  
- Kiosk / wizard flows  

### Phase 6 — Delete old pages (½ day)

After smoke tests pass:

| Action | Paths |
|--------|--------|
| Confirm unused | Grep `render_template` for each candidate |
| Archive remaining orphans | `templates/_archive/20260709-legacy/` |
| Remove root junk | e.g. `tasks_management_mobile.html` at repo root if present |
| Keep | `base.html`, product templates, `modals/`, `components/`, `errors` |
| Do **not** delete | `stitch_kpi_performance_dashboard/` (source library) until migration fully done |
| Update | Any docs still naming old brand/templates |

### Phase 7 — Verify (1 day)

- [ ] `pytest -q` full suite  
- [ ] Manual checklist: each nav item desktop + mobile  
- [ ] Playwright or Chrome DevTools: no console errors, no 404 static assets  
- [ ] Forms: add/edit/delete property, customer, deal, task, agent  
- [ ] Visual spot-check vs Stitch screenshots for 5 hero pages  

---

## 8. Route ↔ template contract (target end state)

| Route | Template | Key context variables |
|-------|----------|----------------------|
| `/` | `dashboard.html` | `stats`, `recent_properties`, `recent_deals`, `pending_tasks`, `recent_activities`, … |
| `/properties` | `properties.html` | `properties`, `pagination`, `form`, filters |
| `/properties/<id>` | `property_details.html` | `property`, `related_properties` |
| `/properties/map` | `map_view.html` | `properties_json` |
| `/agents` | `agents.html` | `agents` |
| `/customers` | `customers.html` | `customers` |
| `/deals` | `deals.html` | `deals`, `pipeline_stats`, `properties`, `customers`, `agents` |
| `/tasks` | `tasks.html` | `tasks`, `agents`, `current_date` |
| `/recommendations` | `recommendations.html` | `customers`, `recommendations`, `selected_customer` |
| `/auth/login` | `auth_login.html` | form / flash |
| `/auth/register` | `auth_register.html` | form / flash |
| `/settings` | `settings_preferences.html` | user / prefs (wire or create route) |
| `/admin/*` | admin templates | existing |

---

## 9. What we will **not** do in this migration

- Rewrite backend models or services for pure UI reasons  
- Introduce React/SPA (stay Jinja + existing JS)  
- Implement every experimental Stitch screen (shader, 3D, unused kiosk)  
- Keep dual brand systems  
- Leave dead templates as live routes  

---

## 10. Risk & mitigations

| Risk | Mitigation |
|------|------------|
| Stitch HTML is static mega-files | Strip chrome; convert only content; componentize |
| Missing context variables | Per-page checklist of route context; Jinja defaults (`|default`) |
| Breaking modals/AJAX | Keep existing IDs/classes used by JS; update JS only when necessary |
| Scope explosion (56 screens) | P0→P1→P2 gates; optional screens after core green |
| Mobile layout drift | Shared base + optional dual content partials |
| Accidental delete of used template | Grep `render_template` before delete; archive first |

---

## 11. Effort estimate

| Phase | Estimate |
|-------|----------|
| 0 Prep + Stitch audit | 0.5 day |
| 1 Shell | 1 day |
| 2 P0 pages | 3–4 days |
| 3 Modals | 1–2 days |
| 4 P1 pages | 1–2 days |
| 5 P2 optional | 2–3 days |
| 6 Delete/cleanup | 0.5 day |
| 7 Verify | 1 day |
| **Core (0–4, 6–7)** | **~8–11 days** |
| **With P2** | **~10–14 days** |

---

## 12. First execution ticket (when approved)

**Start Phase 0 + Phase 1 only:**

1. Sidebar endpoint fix + brand lock  
2. Confirm canonical Stitch screen IDs for P0 pages  
3. Smoke test that current routes still return 200  
4. Then convert **Dashboard** end-to-end as the reference pattern for all other pages  

---

## 13. Success criteria

- [ ] One brand, one design system, one shell across all product pages  
- [ ] All P0 routes use Stitch-derived Jinja templates with **live DB data**  
- [ ] Desktop and mobile usable (no horizontal broken layout, nav works)  
- [ ] Old inconsistent templates not served by any route  
- [ ] Forms, modals, and existing APIs still work  
- [ ] Tests green; manual checklist signed off  

---

## 14. Approval questions (before coding)

1. **Brand display name:** “Platinum Heritage” only, or “EstateSync” with PH visual system?  
2. **Scope gate:** Core P0 only first, or include P1 (map, recommendations, settings, auth) in the same push?  
3. **New pages:** Build Market Analysis + Agent Dashboard routes now, or later?  
4. **Stitch re-generation:** Re-apply design system in Stitch first, or convert from current local HTML as-is?  

**Recommendation:** Brand = Platinum Heritage · Scope = P0 + P1 · New analytics pages = later · Convert from local export + MCP refresh of any missing screens.

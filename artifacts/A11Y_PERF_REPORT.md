# Accessibility & Frontend Performance — Evidence Report

**Branch:** `005-template-replacement`  
**Date:** 2026-07-10  
**Scope:** Track A Flask CRM only  

## Phase 1 baseline (before)

Commands:

```text
$env:PYTHONPATH='.'; python tmp/a11y_perf_baseline.py
```

### Top measured issues (structure)

| Issue | Severity | Evidence |
|-------|----------|----------|
| Multiple `h1` (brand chrome + page title) | serious | 3× h1 on every core route |
| Missing skip-to-content | serious | no skip link / `#main-content` |
| Missing `aria-current="page"` | moderate | active nav only by color/class |
| PHModal: no focus trap / restore | serious | `app-core.js` show/hide only toggled visibility |
| KPI trend color alone | moderate | percent text without textual direction |
| Auth login hard-coded Tailwind CDN + duplicate Material Symbols | perf / a11y | always CDN regardless of `USE_TAILWIND_CDN` |
| External CDN weight | perf | Tailwind CDN (dev), FA, Google Fonts, Material Symbols |

### Top 3 bottlenecks (measured)

1. **Render-blocking third-party CSS/JS** — Font Awesome + Material Symbols + IBM Plex + optional Tailwind CDN on document head.  
2. **Auth standalone pages force Tailwind CDN** — no production CSS path.  
3. **Modal JS incomplete** — keyboard users lose focus management (not transfer size, but interaction cost).

Route TTFB (test client, local SQLite) was already low (most routes &lt; 50ms; dashboard cold ~140ms). **No N+1 optimization applied** — no measured server bottleneck justifying query changes.

Static assets (disk):

| Asset | Bytes |
|-------|------:|
| `static/css/tailwind-ph.css` | 76 237 |
| `static/css/stitch.css` | (local) |
| `static/css/style.css` | (local) |
| `static/js/app-core.js` | (local) |

## Changes implemented

| Area | Files |
|------|--------|
| Skip link, main id, focus-visible, reduced-motion, FA deferred load, app-core `defer` | `templates/base.html` |
| Brand not `h1`; `aria-current="page"` on nav | `templates/components/_sidebar.html`, `_mobile_header.html` |
| Trend sr-only direction text | `templates/dashboard.html` |
| Modal focus trap, Escape, restore opener, `aria-modal` | `static/js/app-core.js` |
| Login production CSS when CDN off | `templates/auth_login.html` |
| Durable tests + CI gate | `tests/test_accessibility_shell.py`, `.github/workflows/tests.yml` |

## After verification

### Automated

```text
python -m pytest -q tests/test_accessibility_shell.py tests/test_platinum_heritage_ui.py tests/test_app_smoke.py tests/test_simple.py tests/test_template_replacement.py tests/test_dashboard_trends.py tests/test_dashboard_template.py --tb=short
→ 83 passed
```

Structure baseline (post-fix): core routes **issues=[]**. Remaining only on standalone `/auth/login` (no CRM shell by design): missing skip/main/aria-current — acceptable for dedicated auth layout; prod CSS path now works when `USE_TAILWIND_CDN=0`.

### Browser (Playwright)

| Check | Result |
|-------|--------|
| Skip link present | 1 |
| `#main-content` | 1 |
| Single `h1` on dashboard | 1 |
| `aria-current="page"` | 1 |
| KPI `.sr-only` trend labels | 4 |
| Open add-property via keyboard Enter | modal visible, `aria-modal=true` |
| Initial focus | `INPUT[name=title]` |
| Escape closes | yes |
| Focus restored to opener | `data-open-modal=addPropertyModal` |
| 320px horizontal overflow | `scrollWidth === clientWidth` (305) |
| Console errors | 0 |

## Form validation accessibility (Task 4 follow-on)

| Item | Status |
|------|--------|
| Label `for`/`id` association | Runtime via `App.initFormAccessibility()`; field `name=` unchanged |
| `aria-required` | Set on required controls |
| `aria-invalid` + `aria-describedby` | Error text `role="alert"` on invalid submit |
| First invalid receives focus | Verified in browser on Add Property |
| Modal titles / Close labels | properties, agents, customers, deals, tasks |
| Flash not color-only | sr-only category prefix |
| Login autocomplete | `username` / `current-password` |

Browser check (Add Property empty submit): `aria-invalid=true`, describedby error, focus on `name=title`, 11 labelled fields.

### Checkpoint 1 — modal keyboard (all core list pages)

| Route | Open | Initial focus | Tab trap (10×) | Escape | Restore opener |
|-------|------|---------------|----------------|--------|----------------|
| `/properties` | yes | `title` | no escape | closes | yes |
| `/customers` | yes | `name` | no escape | closes | yes |
| `/deals` | yes | `property_id` | no escape | closes | yes |
| `/tasks` | yes | `title` | no escape | closes | yes |

Fix note: focusables must not use `offsetParent` (null for `position:fixed`). Sidebar gets `inert` while open; main is not inert (modals live inside `#main-content`).

### Phase 3 — visual / zoom

| Check | Result |
|-------|--------|
| KPI trends not color-only | `.sr-only` direction text |
| Flash not color-only | icon + sr-only category |
| Placeholder contrast | `::placeholder { color:#5d5e5f; opacity:1 }` |
| Disabled contrast | explicit color/border, not faded-only |
| Focus indicator | `:focus-visible` 2px primary ring |
| `prefers-reduced-motion` | transitions/animations minimized |
| 320px dashboard overflow | `scrollWidth === clientWidth` |
| 200% CSS zoom overflow | no extra horizontal scroll measured |

Automated: `tests/test_accessibility_shell.py` includes form helpers + visual style assertions.

## Remaining moderate / follow-up

- Standalone auth/register/kiosk full landmark parity if product requires CRM shell.  
- Font Awesome could be self-hosted later.  
- Server-rendered WTForms error blocks for no-JS clients.  
- Lighthouse LCP/CLS as CI gate remains report-only.  
- Optional prod-CSS pattern on `auth_register.html` / kiosk.

## Phase 4 Task 8 — asset delivery (measured)

### Before (baseline)
- Many pages re-requested **Material Symbols** CSS already in `base.html` (duplicate network hit).
- `auth_register` / kiosk forced **Tailwind CDN**.
- Property modal JS blocked parse without `defer`.
- List images lacked explicit dimensions (CLS risk).

### After

| Optimization | Evidence |
|--------------|----------|
| Strip duplicate Material Symbols from 16 base-extending templates | HTML `Material+Symbols` count **1** on `/properties` |
| Leaflet only on map | `/properties` leaflet=0; `/properties/map` has leaflet |
| Prod CSS on register + kiosk when CDN off | `tailwind-ph.css`, no `cdn.tailwindcss.com` |
| Property list images | `loading="lazy"` + `width/height` + `decoding="async"` |
| Detail hero | `fetchpriority="high"` (LCP), no lazy |
| Gallery thumbs | lazy + dimensions |
| Property modal scripts | `defer` |
| FA non-blocking + app-core defer | already in base |

Browser resource timing sample (`/properties`, prod CSS mode): `tailwindCdn=0`, `tailwindPh=1`, `leaflet=0`, single Material Symbols CSS link in HTML.

### Reproduce

```powershell
$env:PYTHONPATH='.'
$env:USE_TAILWIND_CDN='0'
python main.py
# Browser: http://127.0.0.1:55555/dashboard  (desktop 1440, mobile 320/390)
python -m pytest -q tests/test_accessibility_shell.py --tb=short
python tmp/a11y_perf_baseline.py
```

## Task 9 — server query optimization (measured)

| Route | Before (seed) | After | Fix |
|-------|---------------|-------|-----|
| `/properties` | 10 SQL, **5× property_images** | **6 SQL, 1× images** | `selectinload(Property.images)` (+ agent) |
| `/dashboard` | 17–18 aggregates | ≤18–22 budget | `joinedload` on recent deals; `selectinload` tasks.agent |
| `/deals` | 4–5 | ≤5–10 budget | `joinedload` property/customer/agent |
| `/customers` | 3 | **2** | `selectinload(Customer.deals)` for list counts |

No pagination/filter contract changes. Guarded by `tests/test_query_counts.py` (CI).

## Checkpoint 2 — desktop 1440 & mobile 390 (prod CSS, live server)

| Metric | Result |
|--------|--------|
| Core routes status | 200 |
| Console errors | 0 (excl. favicon noise) |
| Failed static resources | 0 |
| Horizontal overflow | none |
| Landmarks | skip + main + 1 h1 + aria-current |
| Tailwind CDN | 0 |
| Leaflet on non-map | 0 |
| FCP (local) | typically **44–420 ms** (≪ 2.5s LCP target) |
| DCL | typically **36–405 ms** |

LCP entry often absent in short Navigation Timing window without long-lived PerformanceObserver; FCP/DCL used as local proxy and are well under 2.5s.

## Unrelated dirty files

Left untouched: `chroma_db/`, `graphify-out/`, `node_modules/`, `server.pid`, Stitch exports. No commit/push performed.

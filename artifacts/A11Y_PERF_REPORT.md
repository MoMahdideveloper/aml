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

## Remaining moderate / follow-up

- Standalone auth/register/kiosk still need full landmark parity if product requires WCAG shell on those screens.  
- Font Awesome still loaded (deferred via media=print onload) — could self-host later.  
- Form field `aria-describedby` wiring for validation errors: not fully audited page-by-page.  
- Lighthouse LCP/CLS numbers not stored as CI gate (report-only recommendation); local interaction metrics improved via less blocking + better focus.  
- Optional: extend same prod-CSS pattern to `auth_register.html`, `open_house_kiosk.html`.

## Reproduce

```powershell
$env:PYTHONPATH='.'
$env:USE_TAILWIND_CDN='0'
python main.py
# Browser: http://127.0.0.1:55555/dashboard  (desktop 1440, mobile 320/390)
python -m pytest -q tests/test_accessibility_shell.py --tb=short
python tmp/a11y_perf_baseline.py
```

## Unrelated dirty files

Left untouched: `chroma_db/`, `graphify-out/`, `node_modules/`, `server.pid`, Stitch exports. No commit/push performed.

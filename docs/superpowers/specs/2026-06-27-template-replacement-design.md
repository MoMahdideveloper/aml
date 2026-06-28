# Template Replacement Design

## Purpose
Replace existing Flask template files in `templates/` with dynamic pages from Stitch KPI performance dashboard designs while preserving all dynamic functionality.

## Scope
- Convert HTML templates in `templates/` to Jinja2 equivalents using Stitch designs.
- Update static assets (CSS, JS, images) from Stitch designs.
- Ensure template inheritance, data injection, form handling, and AJAX work correctly.
- Do not change Flask routes or backend logic.

## Approach
1. **Analysis**: Map each Flask template to a corresponding Stitch design (see mapping below).
2. **Base Template**: Use existing `templates/base.html` (adjust if needed to include Stitch assets).
3. **Template Conversion**: For each pair:
   - Extract Stitch design HTML.
   - Convert to Jinja2 template extending `base.html`.
   - Replace static content with Jinja2 variables for dynamic data.
   - Preserve blocks for title, page_title, breadcrumb, content, extra_js, etc.
4. **Assets**: Copy CSS, JS, images from Stitch design folders to `static/css/stitch/`, `static/js/stitch/`, `static/img/stitch/`.
5. **Integration**: Verify routes point to correct templates and dynamic data is passed.
6. **Testing**: Run existing test suite to ensure no regressions.

## Mapping (Template -> Stitch Design)
- `dashboard.html` -> `dashboard_overview/code.html`
- `properties.html` -> `property_inventory/code.html`
- `customers.html` -> `clients_management/code.html`
- `deals.html` -> `deals_pipeline/code.html`
- `tasks.html` -> `tasks_management/code.html`
- `agents.html` -> `agent_management/code.html`
- `recommendations.html` -> *(No direct Stitch design; use dashboard_overview as base or create custom)*
- `admin_automations.html` -> *(No direct match; may need custom design)*
- `admin_environment.html` -> *(No direct match; may need custom design)*
- `auth_login.html`, `auth_register.html` -> *(Use Stitch auth designs if available; else customize)*
- Other templates (modals, partials, analysis, etc.) -> Map similarly or create from base.

## Components
- **Base Template**: `templates/base.html` (updated to include Stitch CSS/JS via `url_for`).
- **Content Templates**: Each template under `templates/` extending `base.html`.
- **Static Assets**: 
  - CSS: `static/css/stitch/` (from Stitch design folders)
  - JS: `static/js/stitch/` (from Stitch design folders)
  - Images: `static/img/stitch/` (from design screenshots or assets)
- **Template Blocks**: 
  - `title`, `page_title`, `breadcrumb` (as in existing base)
  - `content` (main area)
  - `extra_js` (for page-specific scripts)
  - `extra_css` (if needed)

## Risks
- Missing Stitch designs for some templates (e.g., recommendations, admin pages) -> Requires custom design or adaptation.
- Dynamic data variables may not match exactly -> Adjust Jinja2 variable names.
- Stitch designs may include incompatible JS/CSS -> Test and adjust.
- Template inheritance may break if blocks are not defined -> Ensure base defines all necessary blocks.

## Acceptance Criteria
- All existing routes render with new Stitch-based templates.
- Dynamic data (properties, customers, etc.) is correctly displayed.
- Forms submit and validate correctly.
- AJAX requests work as before.
- Static assets load without 404 errors.
- Responsive behavior matches Stitch designs.
- Existing test suite passes (no regressions).
- Page load time increase < 20% (if measurable).
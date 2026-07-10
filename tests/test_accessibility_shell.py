"""Durable accessibility shell checks for Track A PH CRM (no pixel assertions)."""

from __future__ import annotations

import re

import pytest


CORE_ROUTES = [
    "/",
    "/dashboard",
    "/properties",
    "/agents",
    "/customers",
    "/deals",
    "/tasks",
    "/recommendations",
    "/settings",
]


@pytest.mark.parametrize("route", CORE_ROUTES)
def test_core_route_landmarks_and_skip(client, db_setup, app, route):
    app.config["USE_TAILWIND_CDN"] = False
    html = client.get(route).get_data(as_text=True)
    assert 'href="#main-content"' in html or "Skip to main content" in html
    assert 'id="main-content"' in html
    assert re.search(r"<main\b", html, re.I)
    assert re.search(r"<nav\b", html, re.I)
    assert re.search(r"<aside\b", html, re.I)
    # Single page-level h1 (brand chrome uses <p>, not h1)
    h1s = re.findall(r"<h1\b", html, flags=re.I)
    assert len(h1s) == 1, f"{route} expected 1 h1, found {len(h1s)}"
    assert 'aria-current="page"' in html
    assert "tailwind-ph.css" in html
    assert "cdn.tailwindcss.com" not in html


def test_dashboard_trend_not_color_only(client, db_setup, app):
    app.config["USE_TAILWIND_CDN"] = False
    html = client.get("/dashboard").get_data(as_text=True)
    assert "sr-only" in html
    assert "Trending" in html or "Unchanged" in html
    assert "vs last month" in html


def test_modal_markup_has_dialog_roles(client, db_setup, app):
    app.config["USE_TAILWIND_CDN"] = False
    html = client.get("/properties").get_data(as_text=True)
    assert 'data-open-modal="addPropertyModal"' in html
    assert 'id="addPropertyModal"' in html
    assert 'role="dialog"' in html
    assert "aria-modal" in html


def test_phmodal_focus_trap_in_app_core():
    from pathlib import Path

    js = Path("static/js/app-core.js").read_text(encoding="utf-8")
    assert "aria-modal" in js
    assert "lastOpener" in js
    assert "trapHandler" in js
    assert "Escape" in js
    assert "Tab" in js
    assert "getClientRects" in js  # fixed-position focusables
    assert "inert" in js


def test_form_accessibility_helpers_in_app_core():
    from pathlib import Path

    js = Path("static/js/app-core.js").read_text(encoding="utf-8")
    assert "initFormAccessibility" in js
    assert "aria-invalid" in js
    assert "aria-describedby" in js
    assert "aria-required" in js
    assert "_markFieldInvalid" in js
    assert "first.focus" in js or "first.focus(" in js
    assert "setBackgroundInert" in js or "inert" in js


def test_visual_a11y_styles_in_base():
    from pathlib import Path

    base = Path("templates/base.html").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in base
    assert "::placeholder" in base
    assert ":disabled" in base
    assert "focus-visible" in base
    assert "max-width: 100%" in base


def test_core_add_modals_have_accessible_titles(client, db_setup, app):
    app.config["USE_TAILWIND_CDN"] = False
    checks = [
        ("/properties", "addPropertyTitle", "addPropertyModal"),
        ("/agents", "addAgentTitle", "addAgentModal"),
        ("/customers", "addCustomerTitle", "addCustomerModal"),
        ("/deals", "addDealTitle", "addDealModal"),
        ("/tasks", "taskModalTitle", "taskModal"),
    ]
    for route, title_id, modal_id in checks:
        html = client.get(route).get_data(as_text=True)
        assert f'id="{modal_id}"' in html
        assert f'id="{title_id}"' in html
        assert "aria-labelledby" in html
        # Icon-only close controls should name themselves
        assert 'aria-label="Close"' in html


def test_reduced_motion_and_skip_styles_in_base():
    from pathlib import Path

    base = Path("templates/base.html").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in base
    assert "skip-link" in base
    assert 'id="main-content"' in base
    assert "defer" in base  # app-core deferred


def test_login_uses_prod_css_when_cdn_off(client, db_setup, app):
    app.config["USE_TAILWIND_CDN"] = False
    html = client.get("/auth/login").get_data(as_text=True)
    assert "tailwind-ph.css" in html
    assert "cdn.tailwindcss.com" not in html


def test_register_uses_prod_css_when_cdn_off(client, db_setup, app):
    app.config["USE_TAILWIND_CDN"] = False
    html = client.get("/auth/register").get_data(as_text=True)
    assert "tailwind-ph.css" in html
    assert "cdn.tailwindcss.com" not in html


def test_core_pages_do_not_double_load_material_symbols(client, db_setup, app):
    """base.html already loads Material Symbols; pages must not request it again."""
    app.config["USE_TAILWIND_CDN"] = False
    marker = "Material+Symbols"
    for route in ("/dashboard", "/properties", "/agents", "/customers", "/deals", "/tasks"):
        html = client.get(route).get_data(as_text=True)
        assert html.count(marker) == 1, f"{route} loads Material Symbols {html.count(marker)} times"


def test_property_list_images_lazy_with_dimensions(client, db_setup, app):
    from pathlib import Path

    app.config["USE_TAILWIND_CDN"] = False
    tpl = Path("templates/properties.html").read_text(encoding="utf-8")
    assert 'loading="lazy"' in tpl
    assert 'width="640"' in tpl
    assert 'height="360"' in tpl
    assert 'decoding="async"' in tpl
    # Deferred property modal scripts (non-critical to first paint)
    assert "property-view-modal.js" in tpl and "defer" in tpl

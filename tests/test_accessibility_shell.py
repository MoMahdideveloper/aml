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

"""Smoke tests for Platinum Heritage UI migration (P0+P1)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROUTES = [
    "/",
    "/dashboard",
    "/properties",
    "/agents",
    "/customers",
    "/deals",
    "/tasks",
    "/recommendations",
    "/properties/map",
    "/market",
    "/compare",
    "/calculators",
    "/messaging",
    "/sms",
    "/contracts",
    "/kiosk",
    "/settings",
    "/auth/login",
    "/auth/register",
]

PAGE_MARKERS = {
    "/": "Platinum Heritage",
    "/properties": "propertyViewModal",  # modal shell always included
    "/agents": "openAgentEdit",
    "/customers": "openCustomerProfile",
    "/deals": "openDealDetail",
    "/tasks": "taskModal",
    "/properties/map": "ph-map",
    "/market": "Market Analysis",
    "/compare": "Property comparison",
    "/calculators": "Investment ROI calculator",
    "/messaging": "Messaging",
    "/sms": "SMS broadcast",
    "/contracts": "Smart contract",
    "/kiosk": "Open house",
}

CORE_TEMPLATES = [
    "base.html",
    "dashboard.html",
    "properties.html",
    "agents.html",
    "agent_dashboard.html",
    "customers.html",
    "deals.html",
    "tasks.html",
    "recommendations.html",
    "map_view.html",
    "settings_preferences.html",
    "market_analysis.html",
    "property_compare.html",
    "roi_calculator.html",
    "messaging.html",
    "sms_broadcast.html",
    "smart_contract.html",
    "open_house_kiosk.html",
    "auth_login.html",
    "auth_register.html",
    "404.html",
    "500.html",
]


def test_health_and_production_css_asset(client, db_setup, app):
    """Health endpoints and prebuilt Tailwind asset exist for production mode."""
    from pathlib import Path

    css = Path("static/css/tailwind-ph.css")
    assert css.exists() and css.stat().st_size > 1000

    hz = client.get("/healthz")
    assert hz.status_code == 200
    assert hz.get_json()["status"] == "ok"

    # Temporarily disable CDN and render base shell
    prev = app.config.get("USE_TAILWIND_CDN")
    app.config["USE_TAILWIND_CDN"] = False
    try:
        with app.test_request_context("/"):
            from flask import render_template_string

            html = render_template_string("{% extends 'base.html' %}{% block content %}ok{% endblock %}")
        assert "tailwind-ph.css" in html
        assert "cdn.tailwindcss.com" not in html
    finally:
        app.config["USE_TAILWIND_CDN"] = prev


def test_property_media_page(client, db_setup):
    """Media manager page loads for a property."""
    from database_service import database_service
    from io import BytesIO

    prop = database_service.add_property(
        title="Media Test Home",
        address="99 Gallery Lane",
        price=400000,
        property_type="house",
        bedrooms=2,
        bathrooms=1,
        square_feet=1100,
        description="Media page test",
    )
    resp = client.get(f"/properties/{prop.id}/media")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Property media" in html
    assert "Upload photos" in html or "Upload" in html

    # Upload a tiny fake PNG
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    up = client.post(
        f"/properties/{prop.id}/media/upload",
        data={"images": (BytesIO(png), "test.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert up.status_code == 200
    assert b"Uploaded" in up.data or b"Gallery" in up.data or b"test" in up.data


def test_agent_dashboard_and_map_pins(client, db_setup):
    """Agent dashboard route + map serves approximate pins when lat/lng missing."""
    from database_service import database_service

    agent = database_service.add_agent(
        "PH Dashboard Agent",
        "ph.dashboard.agent@example.com",
        "555-0100",
        "Luxury residential",
        "Test agent for dashboard smoke",
    )
    agent_id = agent.id
    resp = client.get(f"/agents/{agent_id}")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Agent dashboard" in html or "agent dashboard" in html.lower()
    assert "PH Dashboard Agent" in html

    # Ensure at least one property for map payload
    database_service.add_property(
        title="Map Pin Villa",
        address="123 Main St Downtown",
        price=500000,
        property_type="house",
        bedrooms=3,
        bathrooms=2,
        square_feet=1800,
        description="Map test",
    )

    map_resp = client.get("/properties/map")
    assert map_resp.status_code == 200
    map_html = map_resp.get_data(as_text=True)
    assert "ph-map" in map_html
    assert "L.map" in map_html
    assert "latitude" in map_html or "approx" in map_html


@pytest.mark.parametrize("route", ROUTES)
def test_core_routes_return_ok(client, db_setup, route):
    resp = client.get(route)
    assert resp.status_code < 400, f"{route} returned {resp.status_code}"


@pytest.mark.parametrize("route,marker", list(PAGE_MARKERS.items()))
def test_core_pages_include_ph_markers(client, db_setup, route, marker):
    html = client.get(route).get_data(as_text=True)
    assert marker in html, f"{route} missing marker {marker!r}"


def test_base_shell_is_platinum_heritage():
    content = Path("templates/base.html").read_text(encoding="utf-8")
    assert "Platinum Heritage" in content
    assert "IBM Plex Sans" in content or "IBM+Plex+Sans" in content
    assert "--primary" in Path("static/css/stitch.css").read_text(encoding="utf-8")


def test_core_templates_exist_and_extend_or_stand_alone():
    for name in CORE_TEMPLATES:
        path = Path("templates") / name
        assert path.exists(), f"missing {name}"
        text = path.read_text(encoding="utf-8")
        assert len(text) > 100
        # active app pages should not use legacy luxury tokens
        assert "luxury-primary" not in text
        assert "Luxe Estate" not in text
        assert "LUXE ESTATE" not in text


def test_list_pages_use_data_open_modal(client, db_setup):
    for route, modal_id in [
        ("/properties", "addPropertyModal"),
        ("/agents", "addAgentModal"),
        ("/customers", "addCustomerModal"),
        ("/deals", "addDealModal"),
        ("/tasks", "taskModal"),
    ]:
        html = client.get(route).get_data(as_text=True)
        assert f'data-open-modal="{modal_id}"' in html


def test_active_template_url_for_endpoints_exist(app):
    text = ""
    for p in Path("templates").rglob("*.html"):
        if "_archive" in p.parts:
            continue
        text += p.read_text(encoding="utf-8", errors="ignore") + "\n"
    endpoints = set(re.findall(r"url_for\(\s*['\"]([^'\"]+)['\"]", text))
    missing = sorted(e for e in endpoints if e not in app.view_functions)
    assert not missing, f"Unresolved url_for endpoints: {missing}"

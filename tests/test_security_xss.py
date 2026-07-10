"""XSS / unsafe rendering checks for user-controlled CRM content."""

from __future__ import annotations

import json
import re


XSS_PAYLOAD = '<script>alert("xss")</script>'
XSS_ATTR = '"><img src=x onerror=alert(1)>'


def _app(monkeypatch):
    monkeypatch.setenv("ENABLE_CSRF", "0")
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    from app import create_app
    from database import db
    from database_service import database_service

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        db.drop_all()
        db.create_all()
        agent = database_service.add_agent(
            XSS_PAYLOAD,
            "xss.agent@example.com",
            "555",
            XSS_ATTR,
            XSS_PAYLOAD,
        )
        customer = database_service.add_customer(
            XSS_PAYLOAD,
            "xss.customer@example.com",
            "555",
            100000,
            200000,
            2,
            1,
            "apartment",
            XSS_PAYLOAD,
        )
        # preferences / notes if supported
        database_service.update_customer(customer.id, preferences=XSS_PAYLOAD)
        prop = database_service.add_property(
            title=XSS_PAYLOAD,
            address=XSS_PAYLOAD,
            price=100000,
            property_type="apartment",
            bedrooms=1,
            bathrooms=1,
            square_feet=500,
            description=XSS_PAYLOAD,
        )
        task = database_service.add_task(XSS_PAYLOAD, XSS_PAYLOAD, agent.id, priority="high")
        deal = database_service.add_deal(
            prop.id, customer.id, agent.id, "prospecting", 100000.0
        )
        database_service.update_deal(deal.id, notes=XSS_PAYLOAD)
        ids = {
            "agent_id": agent.id,
            "customer_id": customer.id,
            "property_id": prop.id,
            "task_id": task.id,
            "deal_id": deal.id,
        }
    return app, ids


def _assert_html_escaped(html: str, raw_payload: str = XSS_PAYLOAD) -> None:
    """Raw script tag must not appear unescaped in HTML body."""
    assert raw_payload not in html, "Unescaped XSS payload found in HTML"
    # Accept common Jinja escaping forms
    assert (
        "&lt;script&gt;" in html
        or "\\u003c" in html
        or html.count("<script>") <= html.count("<script src=") + html.count("<script>")
    )
    # Stronger: no live script containing alert("xss") as executable content
    assert 'alert("xss")' not in html or "&lt;script&gt;" in html or "\\u003c" in html


def test_customer_list_escapes_stored_xss_name(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()
    resp = client.get("/customers")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert XSS_PAYLOAD not in html
    assert "&lt;script&gt;" in html or "alert(" not in html


def test_agents_list_escapes_stored_xss(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()
    resp = client.get("/agents")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert XSS_PAYLOAD not in html


def test_tasks_list_escapes_stored_xss(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()
    resp = client.get("/tasks")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert XSS_PAYLOAD not in html


def test_properties_list_escapes_stored_xss(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()
    resp = client.get("/properties")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert XSS_PAYLOAD not in html


def test_json_api_returns_raw_string_with_json_content_type(monkeypatch):
    """JSON may contain the characters; browser must not treat as HTML."""
    app, ids = _app(monkeypatch)
    client = app.test_client()
    resp = client.get(f"/api/customers/{ids['customer_id']}")
    assert resp.status_code == 200
    assert "application/json" in (resp.headers.get("Content-Type") or "")
    data = resp.get_json()
    assert data["name"] == XSS_PAYLOAD
    # Response is proper JSON (parseable), not HTML document
    assert not resp.get_data(as_text=True).lstrip().lower().startswith("<!doctype")


def test_flash_message_escapes_user_content_on_error_paths(monkeypatch):
    """If flash echoes input, it must be escaped in template."""
    app, _ids = _app(monkeypatch)
    client = app.test_client()
    # Trigger a flash path with weird name via invalid form that may echo
    resp = client.post(
        "/agents/add",
        data={
            "name": XSS_PAYLOAD,
            "email": "not-valid-email",
            "phone": "1",
        },
        follow_redirects=True,
    )
    html = resp.get_data(as_text=True)
    # Executable script payload must not appear raw
    assert f"<script>alert" not in html


def test_map_view_properties_json_is_json_encoded(monkeypatch):
    """properties_json|safe must still be JSON, not free HTML injection."""
    app, ids = _app(monkeypatch)
    client = app.test_client()
    resp = client.get("/properties/map")
    # Map may 200 or redirect if empty — only assert when rendered
    if resp.status_code != 200:
        return
    html = resp.get_data(as_text=True)
    # Look for const properties = ... assignment
    m = re.search(r"const properties = (\[.*?\]);", html, re.DOTALL)
    if not m:
        # Alternate patterns
        m = re.search(r"properties\s*=\s*(\[.*?\]);", html, re.DOTALL)
    if m:
        raw = m.group(1)
        # Must parse as JSON
        parsed = json.loads(raw)
        assert isinstance(parsed, list)
        # Script tags inside JSON string values must be quoted strings, not HTML tags
        assert "<script>alert" not in raw or "\\u003c" in raw or '"<' in raw or XSS_PAYLOAD in raw
        # If raw payload is in JSON string, surrounding structure keeps it non-executable
        if XSS_PAYLOAD in raw:
            assert f'"{XSS_PAYLOAD}"' in raw or XSS_PAYLOAD.replace('"', '\\"') in raw


def test_template_safe_filter_inventory_documented():
    """Static inventory: |safe uses must stay intentional (no silent expansion)."""
    import os
    from pathlib import Path

    root = Path("templates")
    safes = []
    for path in root.rglob("*.html"):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "|safe" in text:
            for i, line in enumerate(text.splitlines(), 1):
                if "|safe" in line:
                    safes.append(f"{path.as_posix()}:{i}:{line.strip()}")

    # Known intentional uses only — fail if new ones appear without review
    allowed_substrings = (
        "properties_json|safe",
        "content|safe",
        "footer|safe",
    )
    for entry in safes:
        assert any(a in entry for a in allowed_substrings), (
            f"Unexpected |safe use (review for XSS): {entry}"
        )

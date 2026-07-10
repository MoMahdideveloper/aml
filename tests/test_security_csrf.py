"""CSRF protection for session browser mutations when ENABLE_CSRF=1."""

from __future__ import annotations

import re

import pytest


def _csrf_app(monkeypatch):
    monkeypatch.setenv("ENABLE_CSRF", "1")
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    from app import create_app
    from database import db
    from database_service import database_service

    app = create_app()
    app.config.update(TESTING=True)
    # CSRFProtect is registered; do not disable WTF_CSRF_ENABLED.

    with app.app_context():
        db.drop_all()
        db.create_all()
        database_service.add_agent("Seed Agent", "seed@example.com", "555", "sales", "bio")
        customer = database_service.add_customer(
            "Seed Customer",
            "seed.customer@example.com",
            "555",
            100000,
            200000,
            2,
            1,
            "apartment",
            "city",
        )
        prop = database_service.add_property(
            title="Seed Prop",
            address="1 Seed St",
            price=150000,
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            square_feet=800,
            description="seed",
        )
        deal = database_service.add_deal(prop.id, customer.id, 1, "prospecting", 140000.0)
        task = database_service.add_task("Seed task", "desc", 1, priority="medium")
        ids = {
            "customer_id": customer.id,
            "property_id": prop.id,
            "deal_id": deal.id,
            "task_id": task.id,
            "agent_id": 1,
        }

    assert "csrf" in app.extensions
    return app, ids


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf-token"\s+content="([^"]+)"', html)
    assert m, "Expected csrf-token meta tag when CSRF is enabled"
    return m.group(1)


def _agent_count(app) -> int:
    from database_service import database_service

    with app.app_context():
        return len(database_service.get_agents())


def _customer_count(app) -> int:
    from database_service import database_service

    with app.app_context():
        return len(database_service.get_customers())


def test_base_template_exposes_csrf_meta_when_enabled(monkeypatch):
    app, _ids = _csrf_app(monkeypatch)
    client = app.test_client()
    resp = client.get("/agents")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'name="csrf-token"' in html
    token = _extract_csrf(html)
    assert len(token) > 10


def test_get_reads_unaffected_by_csrf(monkeypatch):
    app, ids = _csrf_app(monkeypatch)
    client = app.test_client()
    assert client.get("/customers").status_code == 200
    assert client.get(f"/api/customers/{ids['customer_id']}").status_code == 200
    assert client.get("/agents").status_code == 200


def test_post_without_csrf_does_not_mutate(monkeypatch):
    app, _ids = _csrf_app(monkeypatch)
    client = app.test_client()
    before = _agent_count(app)

    resp = client.post(
        "/agents/add",
        data={
            "name": "No CSRF Agent",
            "email": "nocsrf@example.com",
            "phone": "555-0001",
            "specialization": "",
            "bio": "",
        },
        follow_redirects=False,
    )
    # Flask-WTF raises 400; app error handler may redirect HTML to dashboard.
    assert resp.status_code in (400, 302, 403)
    if resp.status_code in (301, 302):
        loc = resp.headers.get("Location") or ""
        assert "/agents" not in loc or "dashboard" in loc or loc.endswith("/")
    assert _agent_count(app) == before


def test_post_with_invalid_csrf_does_not_mutate(monkeypatch):
    app, _ids = _csrf_app(monkeypatch)
    client = app.test_client()
    client.get("/agents")  # establish session
    before = _agent_count(app)

    resp = client.post(
        "/agents/add",
        data={
            "name": "Bad Token Agent",
            "email": "badtoken@example.com",
            "phone": "555-0002",
            "specialization": "",
            "bio": "",
            "csrf_token": "not-a-valid-csrf-token",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (400, 302, 403)
    assert _agent_count(app) == before


def test_post_with_valid_csrf_field_succeeds(monkeypatch):
    app, _ids = _csrf_app(monkeypatch)
    client = app.test_client()
    token = _extract_csrf(client.get("/agents").get_data(as_text=True))
    before = _agent_count(app)

    resp = client.post(
        "/agents/add",
        data={
            "name": "Good CSRF Agent",
            "email": "goodcsrf@example.com",
            "phone": "555-0003",
            "specialization": "sales",
            "bio": "",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302)
    assert "/agents" in (resp.headers.get("Location") or "")
    assert _agent_count(app) == before + 1


def test_post_with_valid_csrf_header_succeeds(monkeypatch):
    app, _ids = _csrf_app(monkeypatch)
    client = app.test_client()
    token = _extract_csrf(client.get("/agents").get_data(as_text=True))
    before = _agent_count(app)

    resp = client.post(
        "/agents/add",
        data={
            "name": "Header CSRF Agent",
            "email": "headercsrf@example.com",
            "phone": "555-0004",
            "specialization": "",
            "bio": "",
        },
        headers={"X-CSRFToken": token},
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302)
    assert _agent_count(app) == before + 1


def test_customer_delete_requires_csrf(monkeypatch):
    app, ids = _csrf_app(monkeypatch)
    client = app.test_client()
    before = _customer_count(app)

    resp = client.post(
        f"/customers/{ids['customer_id']}/delete",
        data={},
        follow_redirects=False,
    )
    assert resp.status_code in (400, 302, 403)
    assert _customer_count(app) == before

    token = _extract_csrf(client.get("/customers").get_data(as_text=True))
    # May fail business rule if deals exist — still must pass CSRF first
    resp2 = client.post(
        f"/customers/{ids['customer_id']}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    # CSRF accepted: either redirected after business handling or deleted
    assert resp2.status_code in (200, 301, 302)
    # Not a raw CSRF 400 page with no follow-up handling
    body = resp2.get_data(as_text=True).lower()
    assert "csrf token is missing" not in body


def test_deal_update_and_task_complete_require_csrf(monkeypatch):
    app, ids = _csrf_app(monkeypatch)
    client = app.test_client()

    # Without token — deal status must not flip
    from database_service import database_service

    with app.app_context():
        deal = database_service.get_deal(ids["deal_id"])
        assert deal.status == "prospecting"

    client.post(
        f"/deals/{ids['deal_id']}/update",
        data={"status": "closed_won", "offer_amount": "999999"},
        follow_redirects=False,
    )
    with app.app_context():
        deal = database_service.get_deal(ids["deal_id"])
        assert deal.status == "prospecting"

    token = _extract_csrf(client.get("/deals").get_data(as_text=True))
    client.post(
        f"/deals/{ids['deal_id']}/update",
        data={
            "status": "negotiation",
            "offer_amount": "145000",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    with app.app_context():
        deal = database_service.get_deal(ids["deal_id"])
        assert deal.status == "negotiation"

    # Task complete without CSRF
    with app.app_context():
        task = database_service.get_task(ids["task_id"])
        prior = task.status

    client.post(f"/tasks/{ids['task_id']}/complete", data={}, follow_redirects=False)
    with app.app_context():
        task = database_service.get_task(ids["task_id"])
        assert task.status == prior

    token2 = _extract_csrf(client.get("/tasks").get_data(as_text=True))
    client.post(
        f"/tasks/{ids['task_id']}/complete",
        data={"csrf_token": token2},
        follow_redirects=False,
    )
    with app.app_context():
        task = database_service.get_task(ids["task_id"])
        assert task.status in ("completed", "complete", "done") or task.completed_at is not None


def test_ajax_missing_csrf_returns_json_error(monkeypatch):
    app, _ids = _csrf_app(monkeypatch)
    client = app.test_client()
    client.get("/agents")

    resp = client.post(
        "/agents/add",
        data={
            "name": "Ajax No CSRF",
            "email": "ajaxnocsrf@example.com",
            "phone": "555",
        },
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (400, 403)
    # Prefer structured body without stack traces
    text = resp.get_data(as_text=True)
    assert "Traceback" not in text
    assert "File \"" not in text

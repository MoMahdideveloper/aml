"""Boundary input validation for Track A forms / IDs."""

from __future__ import annotations


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
            "Val Agent", "val.agent@example.com", "555", "sales", "bio"
        )
        customer = database_service.add_customer(
            "Val Customer",
            "val.customer@example.com",
            "555",
            100000,
            200000,
            2,
            1,
            "apartment",
            "city",
        )
        prop = database_service.add_property(
            title="Val Prop",
            address="1 Val St",
            price=100000,
            property_type="apartment",
            bedrooms=1,
            bathrooms=1,
            square_feet=500,
            description="v",
        )
        ids = {
            "agent_id": agent.id,
            "customer_id": customer.id,
            "property_id": prop.id,
        }
    return app, ids


def _customer_count(app) -> int:
    from database_service import database_service

    with app.app_context():
        return len(database_service.get_customers())


def _agent_count(app) -> int:
    from database_service import database_service

    with app.app_context():
        return len(database_service.get_agents())


def test_customer_add_rejects_missing_required_fields(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()
    before = _customer_count(app)

    resp = client.post(
        "/customers/add",
        data={
            "name": "",
            "email": "",
            "phone": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert _customer_count(app) == before
    body = resp.get_data(as_text=True)
    assert "Traceback" not in body
    assert "Internal Server Error" not in body


def test_customer_add_rejects_invalid_email(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()
    before = _customer_count(app)

    resp = client.post(
        "/customers/add",
        data={
            "name": "Bad Email",
            "email": "not-an-email",
            "phone": "555-1111",
            "budget_min": "100000",
            "budget_max": "200000",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert _customer_count(app) == before


def test_customer_add_rejects_excessively_long_name(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()
    before = _customer_count(app)

    resp = client.post(
        "/customers/add",
        data={
            "name": "N" * 500,
            "email": "longname@example.com",
            "phone": "555-2222",
            "budget_min": "0",
            "budget_max": "1",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert _customer_count(app) == before


def test_customer_add_rejects_negative_budget(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()
    before = _customer_count(app)

    resp = client.post(
        "/customers/add",
        data={
            "name": "Neg Budget",
            "email": "negbudget@example.com",
            "phone": "555-3333",
            "budget_min": "-100",
            "budget_max": "-50",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert _customer_count(app) == before


def test_agent_add_rejects_invalid_email(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()
    before = _agent_count(app)

    resp = client.post(
        "/agents/add",
        data={
            "name": "Bad Agent",
            "email": "@@@",
            "phone": "555",
            "specialization": "",
            "bio": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert _agent_count(app) == before


def test_malformed_ids_do_not_500(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()

    for path in (
        "/api/customers/not-an-int",
        "/api/deals/abc",
        "/api/agents/1.5",
        "/customers/xyz/delete",
    ):
        resp = client.get(path) if path.startswith("/api/") else client.post(path, data={})
        assert resp.status_code in (400, 404, 405, 302, 301), f"{path} -> {resp.status_code}"
        text = resp.get_data(as_text=True)
        assert "Traceback (most recent call last)" not in text
        assert "sqlalchemy" not in text.lower() or resp.status_code != 500


def test_deal_add_rejects_missing_foreign_keys(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()

    from database_service import database_service

    with app.app_context():
        before = len(database_service.get_deals())

    resp = client.post(
        "/deals/add",
        data={
            # missing property/customer/agent ids
            "status": "prospecting",
            "offer_amount": "1000",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert len(database_service.get_deals()) == before


def test_task_add_rejects_missing_title_and_agent(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()

    from database_service import database_service

    with app.app_context():
        before = len(database_service.get_tasks())

    resp = client.post(
        "/tasks/add",
        data={"title": "", "description": "x", "agent_id": "", "priority": "medium"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        assert len(database_service.get_tasks()) == before


def test_unknown_query_params_do_not_break_list_pages(monkeypatch):
    app, _ids = _app(monkeypatch)
    client = app.test_client()

    for path in (
        "/customers?evil=<script>&page=999999",
        "/properties?sort=../../../etc/passwd",
        "/agents?filter=%00null",
        "/deals?status=not_a_real_status_hopefully",
    ):
        resp = client.get(path)
        assert resp.status_code in (200, 302, 400)
        assert "Traceback" not in resp.get_data(as_text=True)

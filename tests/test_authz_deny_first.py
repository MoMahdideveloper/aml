"""
Deny-first authorization tests for Track A CRM.

Access model (from code, 2026-07-10) — intentional product behavior:

- **Anonymous**: rejected when AUTH_DEFAULT_DENY_ENABLED=1 (HTML 302, API 401).
- **Authenticated CRM user** (session user_id): global read/write on customers,
  properties, agents, deals, tasks — no per-owner row isolation.
- **Admin** (session admin_authenticated): separate gate for /admin/* env tools.
  Ordinary user session alone is not enough for admin surfaces.

Do not treat "user A can read user B's customer row" as a bug under this model;
document and re-test if product later adds ownership scopes.
"""

from __future__ import annotations

import pytest
from sqlalchemy_models import User


# Representative high-value HTML + API surfaces across domains.
HTML_READ_PATHS = (
    "/customers",
    "/properties",
    "/agents",
    "/deals",
    "/tasks",
    "/recommendations",
)

API_READ_PATHS = (
    "/api/customers/{customer_id}",
    "/api/deals/{deal_id}",
    "/api/agents/{agent_id}",
    "/api/tasks/{task_id}",
    "/api/market-analysis",
)

MUTATING_PATHS = (
    ("POST", "/customers/{customer_id}/delete"),
    ("POST", "/agents/{agent_id}/delete"),
    ("POST", "/deals/{deal_id}/delete"),
    ("POST", "/tasks/{task_id}/delete"),
    ("POST", "/deals/{deal_id}/update"),
)


def _build_authz_app(monkeypatch):
    """Fresh app with default-deny on + synthetic CRM data."""
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "1")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-admin-password")

    from app import create_app
    from database import db
    from database_service import database_service

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    ids = {}
    with app.app_context():
        db.drop_all()
        db.create_all()

        for username, email, role in (
            ("agent_a", "agent_a@example.com", "agent"),
            ("agent_b", "agent_b@example.com", "agent"),
            ("viewer1", "viewer1@example.com", "viewer"),
        ):
            u = User(
                username=username,
                email=email,
                full_name=username.replace("_", " ").title(),
                role=role,
                is_active=True,
            )
            u.set_password("password123")
            db.session.add(u)
        db.session.commit()

        agent = database_service.add_agent(
            "Listing Agent", "listing@example.com", "555-0100", "sales", "bio"
        )
        customer = database_service.add_customer(
            "Secret Customer",
            "secret.customer@example.com",
            "555-0200",
            100000,
            500000,
            3,
            2,
            "apartment",
            "downtown",
        )
        prop = database_service.add_property(
            title="Secret Property",
            address="1 Confidential Ave",
            price=250000,
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            square_feet=900,
            description="sensitive listing notes",
        )
        if hasattr(prop, "agent_id"):
            prop.agent_id = agent.id
            db.session.commit()

        deal = database_service.add_deal(
            prop.id, customer.id, agent.id, "prospecting", 240000.0
        )
        task = database_service.add_task(
            "Call secret customer",
            "Follow up on confidential deal",
            agent.id,
            priority="high",
        )

        ids = {
            "customer_id": customer.id,
            "agent_id": agent.id,
            "property_id": prop.id,
            "deal_id": deal.id,
            "task_id": task.id,
        }

    return app, ids


def _login(client, username: str = "agent_a", password: str = "password123"):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def _format(path: str, ids: dict) -> str:
    try:
        return path.format(**ids)
    except KeyError:
        return path


# ── Task 6: Anonymous deny-first ─────────────────────────────────────────────


def test_anonymous_html_reads_redirect_to_login(monkeypatch):
    app, _ids = _build_authz_app(monkeypatch)
    client = app.test_client()

    for path in HTML_READ_PATHS:
        resp = client.get(path, follow_redirects=False)
        assert resp.status_code in (301, 302), f"{path} status={resp.status_code}"
        location = resp.headers.get("Location") or ""
        assert "/auth/login" in location, f"{path} -> {location}"
        # Denial must not embed protected list content
        body = resp.get_data(as_text=True)
        assert "Secret Customer" not in body
        assert "Secret Property" not in body


def test_anonymous_api_reads_return_401_without_payload(monkeypatch):
    app, ids = _build_authz_app(monkeypatch)
    client = app.test_client()

    for path_t in API_READ_PATHS:
        path = _format(path_t, ids)
        resp = client.get(path)
        assert resp.status_code == 401, f"{path} status={resp.status_code}"
        payload = resp.get_json() or {}
        assert "Unauthorized" in (payload.get("error") or "")
        # No domain data in denial body
        text = resp.get_data(as_text=True)
        assert "Secret Customer" not in text
        assert "secret.customer@example.com" not in text
        assert "Secret Property" not in text
        assert "1 Confidential Ave" not in text


def test_anonymous_mutations_rejected(monkeypatch):
    app, ids = _build_authz_app(monkeypatch)
    client = app.test_client()

    for method, path_t in MUTATING_PATHS:
        path = _format(path_t, ids)
        resp = client.open(path, method=method, follow_redirects=False)
        # 302 login or 401 — must not succeed as 200 that applied mutation
        assert resp.status_code in (301, 302, 401), f"{method} {path} -> {resp.status_code}"
        if resp.status_code in (301, 302):
            assert "/auth/login" in (resp.headers.get("Location") or "")


def test_anonymous_cannot_touch_admin_environment(monkeypatch):
    app, _ids = _build_authz_app(monkeypatch)
    client = app.test_client()

    resp = client.get("/admin/environment", follow_redirects=False)
    assert resp.status_code in (301, 302, 401)
    location = resp.headers.get("Location") or ""
    body = resp.get_data(as_text=True)
    # Must not expose env variable keys in anonymous response body as success page
    if resp.status_code in (301, 302):
        assert "admin/login" in location or "/auth/login" in location
    assert "SESSION_SECRET" not in body or resp.status_code != 200


# ── Task 6: Authenticated ordinary user (global staff CRM) ───────────────────


def test_authenticated_user_can_read_global_crm_lists(monkeypatch):
    app, ids = _build_authz_app(monkeypatch)
    client = app.test_client()
    assert _login(client).status_code in (301, 302)

    for path in HTML_READ_PATHS:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} status={resp.status_code}"

    # Sensitive synthetic data is visible once authenticated (global model).
    cust = client.get(f"/api/customers/{ids['customer_id']}")
    assert cust.status_code == 200
    assert cust.get_json()["name"] == "Secret Customer"

    deal = client.get(f"/api/deals/{ids['deal_id']}")
    assert deal.status_code == 200
    assert deal.get_json()["status"] == "prospecting"


def test_second_authenticated_user_shares_global_data(monkeypatch):
    """IDOR under multi-tenant would fail here; under global staff CRM it is intentional."""
    app, ids = _build_authz_app(monkeypatch)
    client = app.test_client()

    assert _login(client, "agent_b").status_code in (301, 302)

    resp = client.get(f"/api/customers/{ids['customer_id']}")
    assert resp.status_code == 200
    assert resp.get_json()["email"] == "secret.customer@example.com"

    resp = client.get(f"/api/agents/{ids['agent_id']}")
    assert resp.status_code == 200


def test_viewer_role_also_gets_global_crm_access(monkeypatch):
    """user_role is stored but list/detail routes do not enforce role scopes today."""
    app, ids = _build_authz_app(monkeypatch)
    client = app.test_client()
    assert _login(client, "viewer1").status_code in (301, 302)

    resp = client.get(f"/api/customers/{ids['customer_id']}")
    assert resp.status_code == 200
    assert resp.get_json()["name"] == "Secret Customer"


def test_authenticated_missing_ids_are_404_not_auth_error(monkeypatch):
    app, _ids = _build_authz_app(monkeypatch)
    client = app.test_client()
    assert _login(client).status_code in (301, 302)

    for path in (
        "/api/customers/999999",
        "/api/deals/999999",
        "/api/agents/999999",
        "/api/tasks/999999",
    ):
        resp = client.get(path)
        assert resp.status_code == 404, f"{path} -> {resp.status_code}"
        payload = resp.get_json() or {}
        assert "error" in payload
        # Generic not-found; avoid leaking other users' existence patterns beyond 404
        assert "Unauthorized" not in (payload.get("error") or "")


# ── Task 6/7: Admin isolation ────────────────────────────────────────────────


def test_authenticated_crm_user_cannot_access_admin_environment(monkeypatch):
    app, _ids = _build_authz_app(monkeypatch)
    client = app.test_client()
    assert _login(client, "agent_a").status_code in (301, 302)

    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None
        assert sess.get("admin_authenticated") is not True

    resp = client.get("/admin/environment", follow_redirects=False)
    # Must not serve admin env UI as 200 for plain CRM user
    assert resp.status_code in (301, 302, 401, 403)
    if resp.status_code == 200:
        pytest.fail("CRM user must not receive 200 on /admin/environment")
    body = resp.get_data(as_text=True)
    # Successful admin dashboards are large; login redirect/401 should not dump secrets
    assert "GOOGLE_API_KEY" not in body


def test_admin_login_grants_admin_environment_not_via_user_session_alone(monkeypatch):
    app, _ids = _build_authz_app(monkeypatch)
    client = app.test_client()

    # Admin password login (separate from User model)
    resp = client.post(
        "/admin/login",
        data={"password": "test-admin-password"},
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302)
    assert "/admin/environment" in (resp.headers.get("Location") or "")

    with client.session_transaction() as sess:
        assert sess.get("admin_authenticated") is True

    env = client.get("/admin/environment")
    # May 200 with page or still constrained — must not be unauthenticated 401
    assert env.status_code in (200, 302)


def test_wrong_admin_password_does_not_set_admin_session(monkeypatch):
    app, _ids = _build_authz_app(monkeypatch)
    client = app.test_client()

    resp = client.post(
        "/admin/login",
        data={"password": "wrong-password"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get("admin_authenticated") is not True


# ── Task 7: IDOR probes under documented global model ────────────────────────


def test_idor_cross_agent_customer_access_is_allowed_under_global_model(monkeypatch):
    """
    Explicit contract test: any authenticated staff user can load any customer id.
    If product later scopes by owner, invert this assertion and add ownership checks.
    """
    app, ids = _build_authz_app(monkeypatch)
    client = app.test_client()
    assert _login(client, "agent_b").status_code in (301, 302)

    # Tamper: agent_b loads customer/deal/task created in shared office data
    for path in (
        f"/api/customers/{ids['customer_id']}",
        f"/api/deals/{ids['deal_id']}",
        f"/api/tasks/{ids['task_id']}",
        f"/api/agents/{ids['agent_id']}",
    ):
        resp = client.get(path)
        assert resp.status_code == 200, f"expected global allow for {path}"


def test_mutation_by_second_user_affects_shared_record(monkeypatch):
    """Document shared mutability: agent_b can note a deal agent_a office data owns."""
    app, ids = _build_authz_app(monkeypatch)
    client = app.test_client()
    assert _login(client, "agent_b").status_code in (301, 302)

    resp = client.post(
        f"/deals/{ids['deal_id']}/note",
        data={"note": "note-from-agent-b"},
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302, 200)

    # Re-login agent_a and confirm note visible on shared deal (global write)
    client.get("/auth/logout")
    assert _login(client, "agent_a").status_code in (301, 302)
    deal = client.get(f"/api/deals/{ids['deal_id']}")
    assert deal.status_code == 200
    notes = deal.get_json().get("notes") or ""
    assert "note-from-agent-b" in notes


def test_logout_revokes_crm_access(monkeypatch):
    app, ids = _build_authz_app(monkeypatch)
    client = app.test_client()
    assert _login(client).status_code in (301, 302)
    assert client.get(f"/api/customers/{ids['customer_id']}").status_code == 200

    client.get("/auth/logout")
    denied = client.get(f"/api/customers/{ids['customer_id']}")
    assert denied.status_code == 401
    assert "Secret Customer" not in denied.get_data(as_text=True)

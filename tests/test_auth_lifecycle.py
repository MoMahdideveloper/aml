"""Authentication lifecycle: login, logout, redirects, session fixation."""

from __future__ import annotations

from sqlalchemy_models import User


def _build_app(monkeypatch, *, deny: bool = True):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "1" if deny else "0")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    from app import create_app
    from database import db

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        db.drop_all()
        db.create_all()

        active = User(
            username="agent1",
            email="agent1@example.com",
            full_name="Agent One",
            role="agent",
            is_active=True,
        )
        active.set_password("password123")

        inactive = User(
            username="inactive1",
            email="inactive1@example.com",
            full_name="Inactive User",
            role="agent",
            is_active=False,
        )
        inactive.set_password("password123")

        db.session.add_all([active, inactive])
        db.session.commit()

    return app


def test_valid_login_sets_session_and_redirects(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/auth/login",
        data={"username": "agent1", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302)
    assert "/dashboard" in (response.headers.get("Location") or "") or response.headers.get(
        "Location"
    ) in ("/", "/dashboard")

    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None
        assert sess.get("user_role") == "agent"
        assert sess.get("user_name") == "Agent One"


def test_invalid_login_generic_error_and_no_session(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/auth/login",
        data={"username": "agent1", "password": "wrong-password"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    body = response.data.decode("utf-8", errors="replace")
    assert "Invalid username or password" in body
    # Avoid account enumeration messaging
    assert "does not exist" not in body.lower()

    with client.session_transaction() as sess:
        assert sess.get("user_id") is None


def test_logout_clears_session(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    client.post(
        "/auth/login",
        data={"username": "agent1", "password": "password123"},
        follow_redirects=False,
    )
    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None

    response = client.get("/auth/logout", follow_redirects=False)
    assert response.status_code in (301, 302)
    assert "/auth/login" in (response.headers.get("Location") or "")

    with client.session_transaction() as sess:
        assert sess.get("user_id") is None
        assert sess.get("user_role") is None
        assert sess.get("user_name") is None


def test_session_fixation_clears_pre_login_keys(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    with client.session_transaction() as sess:
        sess["attacker_marker"] = "planted-before-login"
        sess["next_url"] = "/customers"

    response = client.post(
        "/auth/login",
        data={"username": "agent1", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302)
    # Safe relative next is honored after fixation clear.
    assert "/customers" in (response.headers.get("Location") or "")

    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None
        assert "attacker_marker" not in sess


def test_open_redirect_rejected_after_login(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/auth/login?next=https://evil.example/phish",
        data={"username": "agent1", "password": "password123"},
        follow_redirects=False,
    )
    assert response.status_code in (301, 302)
    location = response.headers.get("Location") or ""
    assert "evil.example" not in location
    assert location.startswith("/") or "dashboard" in location or location.endswith("/")


def test_open_redirect_protocol_relative_rejected(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/auth/login?next=//evil.example/phish",
        data={"username": "agent1", "password": "password123"},
        follow_redirects=False,
    )
    location = response.headers.get("Location") or ""
    assert "evil.example" not in location


def test_disabled_user_cannot_login(monkeypatch):
    app = _build_app(monkeypatch)
    client = app.test_client()

    response = client.post(
        "/auth/login",
        data={"username": "inactive1", "password": "password123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    body = response.data.decode("utf-8", errors="replace")
    assert "deactivated" in body.lower()

    with client.session_transaction() as sess:
        assert sess.get("user_id") is None


def test_safe_next_from_deny_middleware_round_trip(monkeypatch):
    app = _build_app(monkeypatch, deny=True)
    client = app.test_client()

    denied = client.get("/customers", follow_redirects=False)
    assert denied.status_code in (301, 302)
    assert "/auth/login" in (denied.headers.get("Location") or "")

    with client.session_transaction() as sess:
        assert sess.get("next_url", "").endswith("/customers")

    logged_in = client.post(
        "/auth/login",
        data={"username": "agent1", "password": "password123"},
        follow_redirects=False,
    )
    assert logged_in.status_code in (301, 302)
    assert (logged_in.headers.get("Location") or "").endswith("/customers")

"""Regression tests for auth session cookie hardening."""

from sqlalchemy_models import User


def _build_cookie_test_client(monkeypatch, secure_cookie: bool):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "1")
    monkeypatch.setenv("SESSION_COOKIE_HTTPONLY", "1")
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "Lax")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "1" if secure_cookie else "0")

    from app import create_app
    from database import db

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        db.drop_all()
        db.create_all()

        user = User(
            username="cookieuser",
            email="cookieuser@example.com",
            full_name="Cookie User",
            role="agent",
            is_active=True,
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

    return app.test_client()


def _session_set_cookie_header(response):
    for value in response.headers.getlist("Set-Cookie"):
        if value.startswith("session="):
            return value
    return ""


def test_login_sets_httponly_and_samesite_lax_cookie(monkeypatch):
    client = _build_cookie_test_client(monkeypatch, secure_cookie=False)

    response = client.post(
        "/auth/login",
        data={"username": "cookieuser", "password": "password123"},
        follow_redirects=False,
    )

    assert response.status_code in (301, 302)
    cookie = _session_set_cookie_header(response)
    assert cookie, "Expected session Set-Cookie header"
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" not in cookie


def test_login_sets_secure_cookie_when_enabled(monkeypatch):
    client = _build_cookie_test_client(monkeypatch, secure_cookie=True)

    response = client.post(
        "/auth/login",
        data={"username": "cookieuser", "password": "password123"},
        follow_redirects=False,
    )

    assert response.status_code in (301, 302)
    cookie = _session_set_cookie_header(response)
    assert cookie, "Expected session Set-Cookie header"
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert "Secure" in cookie


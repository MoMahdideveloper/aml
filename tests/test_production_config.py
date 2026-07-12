"""Production configuration contract for create_app()."""

import os

import pytest


DEFAULT_SECRETS = (
    "dev-secret-key-change-in-production",
    "dev",
)


def _fresh_create_app(monkeypatch, **env):
    """Call create_app after isolating production-related env vars."""
    # Clear then set so defaults cannot leak from the shell.
    for key in (
        "FLASK_ENV",
        "ENV",
        "SESSION_SECRET",
        "FLASK_SECRET_KEY",
        "ALLOW_INSECURE_SECRET",
        "ENABLE_CSRF",
        "USE_TAILWIND_CDN",
        "SESSION_COOKIE_SECURE",
        "PREFERRED_URL_SCHEME",
        "ENABLE_CSP",
    ):
        monkeypatch.delenv(key, raising=False)

    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    # Keep tests on in-memory SQLite unless caller overrides.
    monkeypatch.setenv("DATABASE_URL", os.environ.get("DATABASE_URL", "sqlite:///:memory:"))
    # Production app factory also enforces ADMIN_PASSWORD strength.
    if env.get("FLASK_ENV") == "production" and "ADMIN_PASSWORD" not in env:
        monkeypatch.setenv("ADMIN_PASSWORD", "test-strong-admin-password-99")

    from app import create_app

    return create_app()


def test_production_rejects_default_session_secret(monkeypatch):
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        _fresh_create_app(
            monkeypatch,
            FLASK_ENV="production",
            SESSION_SECRET=DEFAULT_SECRETS[0],
        )


def test_production_rejects_missing_session_secret(monkeypatch):
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        _fresh_create_app(monkeypatch, FLASK_ENV="production")


def test_production_allows_insecure_secret_override(monkeypatch):
    app = _fresh_create_app(
        monkeypatch,
        FLASK_ENV="production",
        SESSION_SECRET=DEFAULT_SECRETS[0],
        ALLOW_INSECURE_SECRET="1",
    )
    assert app.secret_key == DEFAULT_SECRETS[0]


def test_production_enables_secure_cookies_csrf_and_built_css(monkeypatch):
    app = _fresh_create_app(
        monkeypatch,
        FLASK_ENV="production",
        SESSION_SECRET="prod-test-secret-not-for-real-use-32chars",
    )
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["USE_TAILWIND_CDN"] is False
    assert app.config["PREFERRED_URL_SCHEME"] == "https"
    # Flask-WTF CSRFProtect registers extension when ENABLE_CSRF defaults on.
    assert "csrf" in app.extensions


def test_test_env_can_disable_csrf_explicitly(monkeypatch):
    app = _fresh_create_app(
        monkeypatch,
        FLASK_ENV="testing",
        SESSION_SECRET="test-secret",
        ENABLE_CSRF="0",
    )
    assert "csrf" not in app.extensions
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()
    # Health endpoint is safe without CSRF
    assert client.get("/healthz").status_code == 200


def test_production_security_headers(monkeypatch):
    app = _fresh_create_app(
        monkeypatch,
        FLASK_ENV="production",
        SESSION_SECRET="prod-test-secret-not-for-real-use-32chars",
    )
    app.config.update(TESTING=True)
    client = app.test_client()
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in (resp.headers.get("Permissions-Policy") or "")
    assert "default-src 'self'" in (resp.headers.get("Content-Security-Policy") or "")
    assert "max-age=" in (resp.headers.get("Strict-Transport-Security") or "")

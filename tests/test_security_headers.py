"""Response security headers (Task 15)."""

from __future__ import annotations


def _app(monkeypatch, **env):
    for key in (
        "FLASK_ENV",
        "ENV",
        "SESSION_SECRET",
        "FLASK_SECRET_KEY",
        "ALLOW_INSECURE_SECRET",
        "ENABLE_CSP",
        "ENABLE_CSRF",
        "AUTH_DEFAULT_DENY_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    from app import create_app

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app


def test_baseline_headers_on_all_envs(monkeypatch):
    app = _app(monkeypatch, FLASK_ENV="development", SESSION_SECRET="dev-test-secret")
    client = app.test_client()
    resp = client.get("/healthz")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert resp.headers.get("X-XSS-Protection") == "0"
    perms = resp.headers.get("Permissions-Policy") or ""
    assert "geolocation=()" in perms
    assert "microphone=()" in perms
    assert "camera=()" in perms


def test_production_enables_csp_and_hsts(monkeypatch):
    app = _app(
        monkeypatch,
        FLASK_ENV="production",
        SESSION_SECRET="prod-test-secret-not-for-real-use-32chars",
    )
    client = app.test_client()
    resp = client.get("/healthz")
    csp = resp.headers.get("Content-Security-Policy") or ""
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "form-action 'self'" in csp
    # No reckless universal script wildcard
    assert "script-src *" not in csp
    assert "default-src *" not in csp
    # Known PH CDNs allowed when used
    assert "fonts.googleapis.com" in csp or "fonts.gstatic.com" in csp
    assert "nominatim.openstreetmap.org" in csp
    hsts = resp.headers.get("Strict-Transport-Security") or ""
    assert "max-age=" in hsts
    assert "includeSubDomains" in hsts


def test_csp_opt_in_for_non_production(monkeypatch):
    app = _app(
        monkeypatch,
        FLASK_ENV="development",
        SESSION_SECRET="dev-test-secret",
        ENABLE_CSP="1",
    )
    client = app.test_client()
    resp = client.get("/healthz")
    csp = resp.headers.get("Content-Security-Policy") or ""
    assert "default-src 'self'" in csp


def test_csp_off_by_default_in_development(monkeypatch):
    app = _app(
        monkeypatch,
        FLASK_ENV="development",
        SESSION_SECRET="dev-test-secret",
        ENABLE_CSP="0",
    )
    client = app.test_client()
    resp = client.get("/healthz")
    # CSP optional in dev (CDN Tailwind debugging)
    assert resp.headers.get("Content-Security-Policy") in (None, "")


def test_sensitive_routes_send_cache_control_no_store(monkeypatch):
    app = _app(
        monkeypatch,
        FLASK_ENV="production",
        SESSION_SECRET="prod-test-secret-not-for-real-use-32chars",
    )
    client = app.test_client()
    # Admin login form is sensitive (credential surface)
    resp = client.get("/admin/login")
    assert resp.status_code == 200
    cache = (resp.headers.get("Cache-Control") or "").lower()
    assert "no-store" in cache or "no-cache" in cache

    # Auth login
    login = client.get("/auth/login")
    assert login.status_code == 200
    cache2 = (login.headers.get("Cache-Control") or "").lower()
    assert "no-store" in cache2 or "no-cache" in cache2


def test_html_pages_also_get_baseline_headers(monkeypatch):
    app = _app(monkeypatch, FLASK_ENV="development", SESSION_SECRET="dev-test-secret")
    client = app.test_client()
    # Use auth HTML shell (no DB tables required)
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"

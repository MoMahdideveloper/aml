"""Security event logging presence + redaction + correlation."""

from __future__ import annotations

import logging

from sqlalchemy_models import User


def _app(monkeypatch, *, deny: bool = False, login_rate_limit: bool = False):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "1" if deny else "0")
    monkeypatch.setenv("ENABLE_CSRF", "0")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("ENABLE_LOGIN_RATE_LIMIT", "1" if login_rate_limit else "0")
    monkeypatch.setenv("LOGIN_RATE_LIMIT", "3 per 1 minute")
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "memory://")

    from app import create_app
    from database import db

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.drop_all()
        db.create_all()
        u = User(
            username="secevt",
            email="secevt@example.com",
            full_name="Sec Event",
            role="agent",
            is_active=True,
        )
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
    return app


def test_login_success_and_failure_emit_events(monkeypatch, caplog):
    app = _app(monkeypatch)
    client = app.test_client()

    with caplog.at_level(logging.INFO, logger="security.events"):
        client.post(
            "/auth/login",
            data={"username": "secevt", "password": "wrong"},
            follow_redirects=False,
        )
        client.post(
            "/auth/login",
            data={"username": "secevt", "password": "password123"},
            follow_redirects=False,
        )
        client.get("/auth/logout")

    text = caplog.text
    assert "event=login_failure" in text
    assert "outcome=invalid_credentials" in text
    assert "event=login_success" in text
    assert "event=logout" in text
    assert "password=password123" not in text
    assert "password=wrong" not in text
    # correlation id attached
    assert "request_id=" in text


def test_auth_denial_emits_event(monkeypatch, caplog):
    app = _app(monkeypatch, deny=True)
    client = app.test_client()
    with caplog.at_level(logging.INFO, logger="security.events"):
        client.get("/customers", follow_redirects=False)
        client.get(
            "/api/market-analysis",
            headers={"Accept": "application/json"},
        )
    assert "event=auth_denial" in caplog.text
    assert "login_required" in caplog.text


def test_request_id_header_round_trip(monkeypatch):
    app = _app(monkeypatch)
    client = app.test_client()
    resp = client.get("/healthz", headers={"X-Request-ID": "client-corr-123"})
    assert resp.headers.get("X-Request-ID") == "client-corr-123"
    # Server also generates when missing
    resp2 = client.get("/healthz")
    assert resp2.headers.get("X-Request-ID")


def test_destructive_delete_logs_event(monkeypatch, caplog):
    app = _app(monkeypatch)
    client = app.test_client()
    from database import db
    from database_service import database_service

    with app.app_context():
        agent = database_service.add_agent(
            "DelMe", "delme@example.com", "555", "x", "b"
        )
        agent_id = agent.id

    with caplog.at_level(logging.INFO, logger="security.events"):
        client.post(f"/agents/{agent_id}/delete", follow_redirects=False)

    assert "event=destructive_action" in caplog.text
    assert "delete_agent" in caplog.text


def test_admin_config_change_logs_without_value(monkeypatch, caplog):
    app = _app(monkeypatch)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["admin_authenticated"] = True
        sess["admin_user"] = "admin"

    secret = "should-never-appear-in-logs-xyz"
    with caplog.at_level(logging.INFO, logger="security.events"):
        client.post(
            "/admin/environment",
            data={
                "key": "AUDIT_PROBE_TOKEN",
                "value": secret,
                "description": "probe",
                "is_required": False,
            },
            follow_redirects=True,
        )
    assert "event=admin_config_change" in caplog.text
    assert "action=create" in caplog.text
    assert "AUDIT_PROBE_TOKEN" in caplog.text
    assert secret not in caplog.text


def test_login_rate_limit_when_enabled(monkeypatch):
    app = _app(monkeypatch, login_rate_limit=True)
    client = app.test_client()
    # 3 per minute allowed
    for _ in range(3):
        r = client.post(
            "/auth/login",
            data={"username": "secevt", "password": "wrong"},
            follow_redirects=False,
        )
        assert r.status_code in (200, 302)
    blocked = client.post(
        "/auth/login",
        data={"username": "secevt", "password": "wrong"},
        follow_redirects=False,
    )
    assert blocked.status_code == 429


def test_redact_sensitive_field_names():
    from utils.security_events import log_security_event
    import logging

    records: list[str] = []

    class H(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    log = logging.getLogger("security.events")
    prev_level = log.level
    prev_propagate = log.propagate
    h = H()
    log.addHandler(h)
    log.setLevel(logging.INFO)
    log.propagate = False
    try:
        log_security_event(
            "test_redact",
            password="should-not-appear",
            api_key="sk-abc",
            username="ok-user",
        )
    finally:
        log.removeHandler(h)
        log.setLevel(prev_level)
        log.propagate = prev_propagate

    joined = " ".join(records)
    assert "should-not-appear" not in joined
    assert "sk-abc" not in joined
    assert "[REDACTED]" in joined
    assert "username=ok-user" in joined

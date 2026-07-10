"""Phase 5: sensitive serialization, admin env redaction, LLM/outbound boundaries."""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────


def _crm_app(monkeypatch, *, deny: bool = False, admin_password: str = "phase5-admin-secret"):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "1" if deny else "0")
    monkeypatch.setenv("ENABLE_CSRF", "0")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("ADMIN_PASSWORD", admin_password)

    from app import create_app
    from database import db
    from database_service import database_service
    from sqlalchemy_models import User

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    ids = {}
    with app.app_context():
        db.drop_all()
        db.create_all()

        user = User(
            username="staff1",
            email="staff1@example.com",
            full_name="Staff One",
            role="agent",
            is_active=True,
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        ids["user_id"] = user.id
        ids["password_hash"] = user.password_hash

        agent = database_service.add_agent(
            "Leak Probe Agent", "leak.agent@example.com", "555", "sales", "bio"
        )
        customer = database_service.add_customer(
            "Leak Probe Customer",
            "leak.customer@example.com",
            "555",
            100000,
            200000,
            2,
            1,
            "apartment",
            "city",
        )
        prop = database_service.add_property(
            title="Leak Prop",
            address="1 Leak St",
            price=100000,
            property_type="apartment",
            bedrooms=1,
            bathrooms=1,
            square_feet=500,
            description="d",
        )
        deal = database_service.add_deal(
            prop.id, customer.id, agent.id, "prospecting", 90000.0
        )
        ids.update(
            {
                "agent_id": agent.id,
                "customer_id": customer.id,
                "property_id": prop.id,
                "deal_id": deal.id,
            }
        )

    return app, ids


def _login_staff(client):
    return client.post(
        "/auth/login",
        data={"username": "staff1", "password": "password123"},
        follow_redirects=False,
    )


def _admin_session(client):
    with client.session_transaction() as sess:
        sess["admin_authenticated"] = True
        sess["admin_user"] = "admin"


# ── Task 12: response serialization ─────────────────────────────────────────


def test_user_to_dict_excludes_password_hash(monkeypatch):
    app, ids = _crm_app(monkeypatch)
    with app.app_context():
        from sqlalchemy_models import User

        from database import db

        user = db.session.get(User, ids["user_id"])
        assert user is not None
        data = user.to_dict()
        assert "password_hash" not in data
        assert "password" not in data
        assert ids["password_hash"] not in json.dumps(data)


def test_api_json_does_not_leak_password_hashes_or_session_secret(monkeypatch):
    app, ids = _crm_app(monkeypatch)
    client = app.test_client()

    for path in (
        f"/api/customers/{ids['customer_id']}",
        f"/api/agents/{ids['agent_id']}",
        f"/api/deals/{ids['deal_id']}",
        f"/api/market-analysis",
    ):
        resp = client.get(path)
        # market-analysis may 200 with stats
        text = resp.get_data(as_text=True)
        assert ids["password_hash"] not in text
        assert "pbkdf2:" not in text
        assert "dev-secret-key-change-in-production" not in text
        assert "SESSION_SECRET" not in text or resp.status_code >= 400


def test_500_json_is_generic_no_traceback(monkeypatch):
    app, _ids = _crm_app(monkeypatch)

    @app.route("/__test_raise_500")
    def _boom():
        raise RuntimeError("secret internals /path/to/file.py SECRET=xyz")

    client = app.test_client()
    resp = client.get(
        "/__test_raise_500",
        headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
    )
    assert resp.status_code == 500
    body = resp.get_json() or {}
    text = resp.get_data(as_text=True)
    assert "Traceback" not in text
    assert "SECRET=xyz" not in text
    assert "/path/to/file.py" not in text
    assert body.get("message")
    assert "unexpected" in (body.get("message") or "").lower() or body.get("error")


def test_health_endpoints_do_not_expose_secrets(monkeypatch):
    app, _ids = _crm_app(monkeypatch)
    client = app.test_client()
    for path in ("/healthz", "/readyz"):
        resp = client.get(path)
        text = resp.get_data(as_text=True)
        assert "password" not in text.lower() or "password" not in (resp.get_json() or {})
        assert "api_key" not in text.lower()
        assert "SECRET" not in text


# ── Task 13: admin environment ───────────────────────────────────────────────


def test_crm_user_cannot_read_admin_environment(monkeypatch):
    app, _ids = _crm_app(monkeypatch, deny=True)
    client = app.test_client()
    assert _login_staff(client).status_code in (301, 302)

    resp = client.get("/admin/environment", follow_redirects=False)
    assert resp.status_code in (301, 302, 401, 403)
    assert resp.status_code != 200 or b"GOOGLE_API_KEY" not in resp.data


def test_sensitive_env_var_masked_on_list_and_details(monkeypatch, caplog):
    app, _ids = _crm_app(monkeypatch)
    client = app.test_client()
    _admin_session(client)

    from database import db
    from services.environment_service import environment_service

    # Sensitive pattern (TOKEN) but not protected *_API_KEY / infra keys
    secret_key = "CUSTOM_WEBHOOK_TOKEN"
    secret_value = "super-secret-api-key-value-999"
    with app.app_context():
        result = environment_service.create_variable(
            key=secret_key,
            value=secret_value,
            description="phase5 probe",
            is_required=False,
            created_by="admin",
        )
        assert result.get("is_sensitive") is True
        assert secret_value not in (result.get("value") or "")
        assert "*" in (result.get("value") or "")

    # List page (HTML)
    with caplog.at_level(logging.INFO):
        page = client.get("/admin/environment")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert secret_value not in html

    # Details AJAX (decrypt=False → masked)
    details = client.get(f"/admin/environment/{secret_key}/details")
    assert details.status_code == 200
    payload = details.get_json()
    assert payload.get("success") is True
    var = payload.get("variable") or {}
    assert secret_value not in (var.get("value") or "")
    assert var.get("is_sensitive") is True

    # History must not expose plaintext secret
    hist = client.get("/admin/environment/history")
    assert hist.status_code == 200
    assert secret_value not in hist.get_data(as_text=True)

    # Logs from this operation should not contain the secret value
    assert secret_value not in caplog.text


def test_create_variable_response_masks_sensitive_and_rolls_back_on_dup(monkeypatch):
    app, _ids = _crm_app(monkeypatch)
    from services.environment_service import environment_service

    with app.app_context():
        environment_service.create_variable(
            key="DUP_TOKEN",
            value="token-value-abc",
            created_by="admin",
        )
        with pytest.raises(ValueError, match="already exists"):
            environment_service.create_variable(
                key="DUP_TOKEN",
                value="other-value",
                created_by="admin",
            )
        # Still one row
        from sqlalchemy_models import EnvironmentVariable

        assert EnvironmentVariable.query.filter_by(key="DUP_TOKEN").count() == 1


def test_ordinary_user_api_cannot_fetch_env_details(monkeypatch):
    app, _ids = _crm_app(monkeypatch, deny=True)
    client = app.test_client()
    assert _login_staff(client).status_code in (301, 302)

    resp = client.get(
        "/admin/environment/CUSTOM_WEBHOOK_TOKEN/details",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code in (301, 302, 401, 403)
    text = resp.get_data(as_text=True)
    assert "super-secret" not in text


# ── Task 14: LLM / outbound ──────────────────────────────────────────────────


def test_extract_from_text_uses_service_and_returns_structured_dict(monkeypatch):
    app, _ids = _crm_app(monkeypatch)
    client = app.test_client()

    fake = {
        "entity": "property",
        "data": {
            "title": "AI Villa",
            "address": "1 AI St",
            "price": 100,
            "property_type": "villa",
        },
        "missing": [],
        "confidence": 0.9,
    }

    with patch(
        "views.property_listing.gemini_service.extract_property_from_text",
        return_value=fake,
    ) as mocked:
        # Import path may be services — also patch database-facing module used by view
        with patch(
            "services.gemini_service.gemini_service.extract_property_from_text",
            return_value=fake,
        ):
            resp = client.post(
                "/properties/extract-from-text",
                json={"text": "3br villa downtown for sale"},
                headers={"Content-Type": "application/json"},
            )

    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data.get("title") == "AI Villa"
    # No stack / no raw exception
    assert "Traceback" not in resp.get_data(as_text=True)


def test_extract_from_text_rejects_empty_and_handles_provider_failure(monkeypatch):
    app, _ids = _crm_app(monkeypatch)
    client = app.test_client()

    empty = client.post(
        "/properties/extract-from-text",
        json={"text": "   "},
        headers={"Content-Type": "application/json"},
    )
    assert empty.status_code == 400

    with patch(
        "services.gemini_service.gemini_service.extract_property_from_text",
        side_effect=RuntimeError("provider down"),
    ):
        # View imports gemini_service at call site — patch common symbols
        import services.gemini_service as gs

        with patch.object(
            gs.gemini_service,
            "extract_property_from_text",
            side_effect=RuntimeError("provider down"),
        ):
            fail = client.post(
                "/properties/extract-from-text",
                json={"text": "some listing text here"},
                headers={"Content-Type": "application/json"},
            )
    assert fail.status_code == 500
    body = fail.get_json() or {}
    assert "provider down" not in json.dumps(body)
    assert body.get("error")


def test_llm_providers_have_timeouts_configured():
    from services.llm.providers.kie_provider import KieProvider
    from services.llm.providers.gemini_provider import GeminiProvider

    kie = KieProvider()
    assert kie.timeout_seconds > 0
    assert kie.timeout_seconds <= 120

    gem = GeminiProvider()
    assert gem.request_timeout_seconds > 0
    assert gem.request_timeout_seconds <= 120


def test_nominatim_geocode_only_hits_fixed_host(monkeypatch):
    """User free-text must not become an arbitrary outbound URL (SSRF)."""
    import services.geo_service as geo

    captured = {}

    class FakeResp:
        def read(self):
            return b'[{"lat":"35.0","lon":"51.0"}]'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["full_url"] = req.full_url
        captured["timeout"] = timeout
        return FakeResp()

    monkeypatch.setenv("GEOCODE_PROVIDER", "nominatim")
    geo._NOMINATIM_CACHE.clear()
    with patch("services.geo_service.urllib.request.urlopen", side_effect=fake_urlopen):
        result = geo.nominatim_geocode("Tehran Niyavaran street 1")

    assert result == (35.0, 51.0)
    assert captured["full_url"].startswith("https://nominatim.openstreetmap.org/search?")
    assert "evil.example" not in captured["full_url"]
    # Query is param, not host
    assert "Tehran" in captured["full_url"] or "Niyavaran" in captured["full_url"] or "q=" in captured["full_url"]
    assert captured["timeout"] is not None


def test_llm_malicious_payload_not_executed_as_code(monkeypatch):
    """Provider returning script-like fields stays data; never eval'd."""
    app, _ids = _crm_app(monkeypatch)
    client = app.test_client()

    evil = {
        "entity": "property",
        "data": {
            "title": '<script>alert(1)</script>',
            "description": "__import__('os').system('id')",
        },
        "missing": [],
        "confidence": 0.5,
    }

    import services.gemini_service as gs

    with patch.object(gs.gemini_service, "extract_property_from_text", return_value=evil):
        resp = client.post(
            "/properties/extract-from-text",
            json={"text": "payload"},
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"].startswith("<script>")
    # Still pure JSON data — client must not eval
    assert resp.headers.get("Content-Type", "").startswith("application/json")

"""AI form assist API — auth, no CRM writes, mocked extractor."""

import json

import pytest

from services.ai_form_assist.gemini_extractor import GeminiFormExtractor
from services.ai_form_assist.service import AIFormAssistService
from services.ai_form_assist.storage import PrivateAuditStorage
from services.ai_form_assist.types import ExtractionResult, RawFieldSuggestion, SourceType
from sqlalchemy_models import Property, User


class _FakeModels:
    def generate_content(self, **kwargs):
        payload = {
            "fields": [
                {"field": "title", "value": "AI Villa", "confidence": 0.95},
                {"field": "sale_price", "value": 900000, "confidence": 0.8},
            ]
        }
        return type("R", (), {"text": json.dumps(payload)})()


class _FakeClient:
    models = _FakeModels()


@pytest.fixture()
def api_client(db_setup, app, monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "1")
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    store = PrivateAuditStorage(root=tmp_path / "audit")
    extractor = GeminiFormExtractor(client=_FakeClient(), fast_model="test-model")
    svc = AIFormAssistService(extractor=extractor, storage=store)
    monkeypatch.setattr(
        "services.ai_form_assist.service.ai_form_assist_service", svc
    )
    monkeypatch.setattr("views.ai_form_assist.ai_form_assist_service", svc, raising=False)
    # re-bind module-level import used by views
    import views.ai_form_assist as vap

    monkeypatch.setattr(
        "services.ai_form_assist.service.AIFormAssistService",
        lambda **kw: svc,
    )
    with app.app_context():
        from database import db

        u = User(username="aiform", email="aiform@test.com", role="agent", is_active=True)
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
        uid = u.id
    client = app.test_client()
    client.post(
        "/auth/login",
        data={"username": "aiform", "password": "password123"},
        follow_redirects=False,
    )
    return client, svc, uid


def test_unauthorized_create(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "1")
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    c = app.test_client()
    r = c.post("/api/ai-form-assist/extractions", data={"form": "property", "text": "x"})
    assert r.status_code == 401


def test_disabled_returns_404(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "0")
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    c = app.test_client()
    with app.app_context():
        from database import db

        u = User(username="off", email="off@test.com", role="agent", is_active=True)
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
    c.post("/auth/login", data={"username": "off", "password": "password123"})
    r = c.post("/api/ai-form-assist/extractions", data={"form": "property", "text": "x"})
    assert r.status_code == 404


def test_create_get_review_no_crm_write(api_client, app, monkeypatch, tmp_path):
    client, svc, uid = api_client
    # inject service into view by patching create path
    from services.ai_form_assist import service as svc_mod

    monkeypatch.setattr(svc_mod, "ai_form_assist_service", svc)

    with app.app_context():
        before = Property.query.count()

    r = client.post(
        "/api/ai-form-assist/extractions",
        data={
            "form": "property",
            "text": "Beautiful villa",
            "existing_values_json": json.dumps({"title": ""}),
            "idempotency_key": "k1",
        },
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert body["crm_written"] is False
    assert body["form_name"] == "property"
    assert any(s["field"] == "title" for s in body["suggestions"])
    eid = body["id"]

    r2 = client.get(f"/api/ai-form-assist/extractions/{eid}")
    assert r2.status_code == 200
    assert r2.get_json()["id"] == eid

    r3 = client.post(
        f"/api/ai-form-assist/extractions/{eid}/review",
        json={"decisions": [{"field": "title", "decision": "accept", "suggestion_id": body["suggestions"][0]["id"]}]},
        content_type="application/json",
    )
    assert r3.status_code == 200
    assert r3.get_json()["crm_written"] is False

    with app.app_context():
        assert Property.query.count() == before


def test_missing_modality(api_client, app, monkeypatch):
    client, svc, _ = api_client
    from services.ai_form_assist import service as svc_mod

    monkeypatch.setattr(svc_mod, "ai_form_assist_service", svc)
    r = client.post("/api/ai-form-assist/extractions", data={"form": "property", "text": ""})
    assert r.status_code == 400
    assert r.get_json()["error"] == "missing_modality"


def test_unknown_form(api_client, app, monkeypatch):
    client, svc, _ = api_client
    from services.ai_form_assist import service as svc_mod

    monkeypatch.setattr(svc_mod, "ai_form_assist_service", svc)
    r = client.post(
        "/api/ai-form-assist/extractions",
        data={"form": "not_a_form", "text": "hello world"},
    )
    assert r.status_code == 400

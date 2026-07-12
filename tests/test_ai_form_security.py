"""Security: AI form assist never writes CRM; unauthorized blocked."""

import json

from services.ai_form_assist.gemini_extractor import GeminiFormExtractor
from services.ai_form_assist.service import AIFormAssistService
from services.ai_form_assist.storage import PrivateAuditStorage
from sqlalchemy_models import Customer, Property, User


class _FakeModels:
    def generate_content(self, **kwargs):
        return type(
            "R",
            (),
            {
                "text": json.dumps(
                    {"fields": [{"field": "title", "value": "X", "confidence": 0.99}]}
                )
            },
        )()


def test_service_does_not_create_property(db_setup, app, tmp_path):
    with app.app_context():
        from database import db

        before_p = Property.query.count()
        before_c = Customer.query.count()
        svc = AIFormAssistService(
            extractor=GeminiFormExtractor(
                client=type("C", (), {"models": _FakeModels()})(),
                fast_model="t",
            ),
            storage=PrivateAuditStorage(root=tmp_path / "a"),
        )
        out = svc.create_extraction(
            form_name="property",
            actor_user_id=1,
            text="villa near downtown",
            existing_values={},
        )
        assert out["crm_written"] is False
        assert Property.query.count() == before_p
        assert Customer.query.count() == before_c


def test_forbidden_other_users_extraction(db_setup, app, tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "1")
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")
    store = PrivateAuditStorage(root=tmp_path / "a")
    svc = AIFormAssistService(
        extractor=GeminiFormExtractor(
            client=type("C", (), {"models": _FakeModels()})(),
            fast_model="t",
        ),
        storage=store,
    )
    with app.app_context():
        from database import db
        from services.ai_form_assist import service as svc_mod

        u1 = User(username="u1", email="u1@t.com", role="agent", is_active=True)
        u1.set_password("password123")
        u2 = User(username="u2", email="u2@t.com", role="agent", is_active=True)
        u2.set_password("password123")
        db.session.add_all([u1, u2])
        db.session.commit()
        out = svc.create_extraction(
            form_name="property",
            actor_user_id=u1.id,
            text="something long enough",
        )
        eid = out["id"]

    import views.ai_form_assist as vap
    monkeypatch.setattr("services.ai_form_assist.service.ai_form_assist_service", svc)

    c = app.test_client()
    c.post("/auth/login", data={"username": "u2", "password": "password123"})
    r = c.get(f"/api/ai-form-assist/extractions/{eid}")
    assert r.status_code in (403, 404)

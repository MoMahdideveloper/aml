"""Grounded AI answer service (deterministic path)."""

from services.ai_answer_service import AnswerError, answer, feature_enabled
from sqlalchemy_models import Customer


def test_answer_disabled(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_ANSWER", "0")
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    with app.app_context():
        try:
            answer("customer", 1, "What is their budget?")
            assert False, "expected disabled"
        except AnswerError as e:
            assert e.code == "disabled"


def test_deterministic_answer(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_ANSWER", "1")
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    with app.app_context():
        from database import db

        c = Customer(
            name="Answer User",
            email="ans@example.com",
            phone="5559000001",
            budget_min=100,
            budget_max=250000,
            preferred_type="villa",
        )
        db.session.add(c)
        db.session.commit()

        # Force no LLM
        import services.ai_answer_service as mod

        class _NoLLM:
            is_available = False

        monkeypatch.setattr(mod, "feature_enabled", lambda: True)
        # patch llm import inside answer
        import services.llm as llm_mod

        monkeypatch.setattr(llm_mod, "llm_provider", _NoLLM(), raising=False)

        result = answer("customer", c.id, "What is the budget max?")
        assert result["entity_id"] == c.id
        assert result["mode"] in ("deterministic", "deterministic_fallback", "llm")
        assert "Answer User" in result["answer"] or "budget" in result["answer"].lower() or "250" in result["answer"]
        assert isinstance(result["evidence"], list)
        assert len(result["evidence"]) >= 1


def test_answer_route(client, db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_ANSWER", "1")
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    with app.app_context():
        from database import db
        from sqlalchemy_models import User

        c = Customer(
            name="Route Ans",
            email="routeans@example.com",
            phone="5559000002",
            budget_max=99,
        )
        u = User(
            username="ansstaff",
            email="ansstaff@example.com",
            full_name="A",
            role="agent",
            is_active=True,
        )
        u.set_password("password123")
        db.session.add_all([c, u])
        db.session.commit()
        cid = c.id

    client.post("/auth/login", data={"username": "ansstaff", "password": "password123"})
    r = client.post(
        f"/api/context/customer/{cid}/answer",
        json={"question": "Summarize this customer"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data["entity_id"] == cid
    assert "answer" in data

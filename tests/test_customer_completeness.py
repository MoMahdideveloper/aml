"""Customer completeness checklist (structured fields only)."""

from services.customer_completeness import evaluate_customer_completeness
from sqlalchemy_models import Customer


def test_missing_budget_and_beds():
    class C:
        budget_min = 0
        budget_max = 0
        preferred_bedrooms = 0
        preferred_bathrooms = 0
        preferred_type = ""
        location_preference = ""
        status = "active"

    s = evaluate_customer_completeness(C())
    assert s["complete"] is False
    assert "budget_min" in s["missing"]
    assert "preferred_bedrooms" in s["missing"]
    assert "status" in s["present"]
    assert s["score"] < 1.0


def test_full_profile_complete():
    class C:
        budget_min = 100
        budget_max = 500
        preferred_bedrooms = 2
        preferred_bathrooms = 1
        preferred_type = "apartment"
        location_preference = "downtown"
        status = "active"
        preferences = "should not be inspected as completeness signal alone"

    s = evaluate_customer_completeness(C())
    assert s["complete"] is True
    assert s["missing"] == []
    assert s["score"] == 1.0


def test_context_includes_completeness(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    with app.app_context():
        from database import db
        from services.context_builder import ContextBuilder

        c = Customer(
            name="Comp Test",
            email="comp@example.com",
            phone="5558000001",
            status="active",
            budget_min=0,
            budget_max=0,
            preferred_bedrooms=0,
        )
        db.session.add(c)
        db.session.commit()
        packet = ContextBuilder().build("customer", c.id, purpose="brief")
        data = packet.to_dict()
        assert "completeness" in data["sections"]
        missing = data["sections"]["completeness"]["missing"]["value"]
        assert "budget_max" in missing or "budget_min" in missing

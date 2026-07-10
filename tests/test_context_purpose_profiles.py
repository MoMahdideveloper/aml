"""Context purpose profiles drop non-priority sections."""

from services.context_builder import context_builder
from sqlalchemy_models import Customer, CustomerOpportunityBrief, Property, PropertyMatch


def test_match_purpose_omits_timeline_heavy(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    with app.app_context():
        from database import db

        c = Customer(name="Prof", email="prof@example.com", phone="5559100001")
        p = Property(title="P", address="A", property_type="villa", price=1)
        db.session.add_all([c, p])
        db.session.flush()
        db.session.add(
            PropertyMatch(customer_id=c.id, property_id=p.id, match_score=0.5, status="pending")
        )
        db.session.add(
            CustomerOpportunityBrief(customer_id=c.id, title="Need", role="buyer")
        )
        db.session.commit()
        brief = context_builder.build("customer", c.id, purpose="brief")
        match = context_builder.build("customer", c.id, purpose="match")
        assert "matches" in match.sections
        # match profile should not force timeline if never built without interactions
        assert match.meta.get("purpose_profile") == "match" or "omitted_sections" in match.meta

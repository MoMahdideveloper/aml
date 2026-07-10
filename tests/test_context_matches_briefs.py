"""Context includes matches and opportunity briefs."""

from services.context_builder import context_builder
from sqlalchemy_models import (
    Customer,
    CustomerOpportunityBrief,
    Property,
    PropertyMatch,
)


def test_customer_context_has_matches_and_briefs(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    with app.app_context():
        from database import db

        c = Customer(
            name="Match Ctx",
            email="matchctx@example.com",
            phone="5558000001",
        )
        p = Property(title="Match Prop", address="1", property_type="villa", price=100)
        db.session.add_all([c, p])
        db.session.flush()
        db.session.add(
            PropertyMatch(
                property_id=p.id,
                customer_id=c.id,
                match_score=0.88,
                status="pending",
            )
        )
        db.session.add(
            CustomerOpportunityBrief(
                customer_id=c.id,
                title="Buy villa",
                role="buyer",
                budget_max=500000,
                preferred_type="villa",
            )
        )
        db.session.commit()
        packet = context_builder.build("customer", c.id)
        assert "matches" in packet.sections
        assert packet.sections["matches"][0]["match_score"]["value"] == 0.88
        assert "opportunity_briefs" in packet.sections
        assert packet.sections["opportunity_briefs"][0]["title"]["value"] == "Buy villa"

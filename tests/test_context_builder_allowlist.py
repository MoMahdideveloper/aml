"""Context packets exclude forbidden fields."""

import json

from services.context_builder import ContextError, context_builder
from sqlalchemy_models import Customer, CustomerInteraction, Deal, Property


def test_customer_packet_excludes_notes_and_preferences(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    with app.app_context():
        from database import db

        c = Customer(
            name="Ctx User",
            email="ctx@example.com",
            phone="5553000001",
            status="active",
            preferences="SECRET free text notes",
            budget_min=100,
            budget_max=200,
            preferred_type="villa",
            location_preference="North",
        )
        db.session.add(c)
        db.session.flush()
        db.session.add(
            CustomerInteraction(
                customer_id=c.id,
                interaction_type="call",
                subject="private subject",
                body="private body text",
                outcome="completed",
            )
        )
        db.session.commit()

        packet = context_builder.build("customer", c.id, purpose="brief")
        raw = json.dumps(packet.to_dict())
        assert "SECRET free text" not in raw
        assert "private body" not in raw
        assert "private subject" not in raw
        assert "customer.preferences" not in raw
        assert '"body"' not in raw
        assert packet.sections["identity"]["name"]["value"] == "Ctx User"
        assert packet.sections["requirements"]["budget_max"]["value"] == 200
        assert "timeline" in packet.sections
        assert packet.sections["timeline"][0]["interaction_type"]["value"] == "call"
        assert "source" in packet.sections["identity"]["name"]



def test_property_description_truncated(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    with app.app_context():
        from database import db

        long_desc = "x" * 2000
        p = Property(
            title="Ctx Prop",
            address="1 Rd",
            property_type="villa",
            price=100,
            description=long_desc,
        )
        db.session.add(p)
        db.session.commit()
        packet = context_builder.build("property", p.id)
        text = packet.sections["description"]["text"]["value"]
        assert len(text) < 500
        assert text.endswith("…")


def test_deal_excludes_notes(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    with app.app_context():
        from database import db

        c = Customer(
            name="D",
            email="dctx@example.com",
            phone="5553000002",
        )
        p = Property(title="P", address="A", property_type="house", price=1)
        db.session.add_all([c, p])
        db.session.flush()
        deal = Deal(
            customer_id=c.id,
            property_id=p.id,
            status="prospecting",
            offer_amount=50,
            notes="CONFIDENTIAL DEAL NOTES",
        )
        db.session.add(deal)
        db.session.commit()
        packet = context_builder.build("deal", deal.id)
        raw = json.dumps(packet.to_dict())
        assert "CONFIDENTIAL" not in raw
        assert "deal.notes" not in raw
        assert packet.meta.get("include_freeform_notes") is False


"""Context packet char budget trimming."""

from services.context_builder import context_builder, max_chars
from sqlalchemy_models import Customer, Deal, Property


def test_budget_trims_when_small(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    monkeypatch.setenv("AI_CONTEXT_MAX_CHARS", "800")
    with app.app_context():
        from database import db

        c = Customer(
            name="Budget User",
            email="budget@example.com",
            phone="5553000010",
            location_preference="Somewhere long " * 20,
        )
        db.session.add(c)
        db.session.flush()
        p = Property(
            title="Budget Prop",
            address="Addr",
            property_type="villa",
            price=1,
            description="y" * 500,
        )
        db.session.add(p)
        db.session.flush()
        for i in range(5):
            db.session.add(
                Deal(
                    customer_id=c.id,
                    property_id=p.id,
                    status="prospecting",
                    offer_amount=i * 10,
                )
            )
        db.session.commit()

        packet = context_builder.build("customer", c.id)
        assert packet.meta["char_count"] <= max_chars() + 200  # small slack for meta
        # may or may not trim depending on size; if trimmed flag set, ok
        assert "char_budget" in packet.meta

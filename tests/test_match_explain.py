"""Match explanation helpers for Customer 360."""

import json

from services.match_explain import _parse_reasons, list_customer_matches
from sqlalchemy_models import Customer, Property, PropertyMatch


def test_parse_reasons_json_list():
    assert _parse_reasons(json.dumps(["Budget fit", "Location match"])) == [
        "Budget fit",
        "Location match",
    ]


def test_list_customer_matches(db_setup, app):
    with app.app_context():
        from database import db

        c = Customer(name="MX", email="mx@example.com", phone="5559200001")
        p = Property(title="Matched Villa", address="1", property_type="villa", price=100)
        db.session.add_all([c, p])
        db.session.flush()
        db.session.add(
            PropertyMatch(
                customer_id=c.id,
                property_id=p.id,
                match_score=0.82,
                status="pending",
                confidence_level="high",
                match_reasons=json.dumps(["Type match", "Budget in range"]),
            )
        )
        db.session.commit()
        rows = list_customer_matches(c.id)
        assert len(rows) == 1
        assert rows[0]["property_title"] == "Matched Villa"
        assert rows[0]["why"] == ["Type match", "Budget in range"]
        assert rows[0]["match_score"] == 0.82
        assert "score_components" in rows[0]
        assert "property_id" in rows[0]


def test_list_customer_matches_skips_deleted_property_and_customer(db_setup, app):
    with app.app_context():
        from database import db

        c = Customer(name="MX2", email="mx2@example.com", phone="5559200002")
        p = Property(
            title="Gone",
            address="1",
            property_type="villa",
            price=100,
            is_deleted=True,
        )
        db.session.add_all([c, p])
        db.session.flush()
        db.session.add(
            PropertyMatch(
                customer_id=c.id,
                property_id=p.id,
                match_score=0.9,
                status="pending",
                match_reasons=json.dumps(["should not show"]),
            )
        )
        db.session.commit()
        assert list_customer_matches(c.id) == []

        c.is_deleted = True
        db.session.commit()
        assert list_customer_matches(c.id) == []

"""Hybrid results include explainable evidence."""

from services.hybrid_search import hybrid_search_service
from services.unified_search import parse_search_request
from sqlalchemy_models import Property


def test_hit_evidence_shape(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "1")
    with app.app_context():
        from database import db

        db.session.add(
            Property(
                title="Evidence Villa",
                address="9",
                property_type="villa",
                price=100,
                bedrooms=3,
            )
        )
        db.session.commit()
        req = parse_search_request(q="Evidence", scope="properties", mode="full")
        result = hybrid_search_service.search(req)
        hits = result["groups"]["properties"]
        assert hits
        ev = hits[0].get("evidence")
        assert ev is not None
        assert "why" in ev
        assert "filters_hard" in ev
        assert "filters_soft" in ev

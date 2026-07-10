"""Description search only when flag on."""

from services.unified_search import parse_search_request, unified_search_service
from sqlalchemy_models import Property


def test_description_not_searched_by_default(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_DESCRIPTION_SEARCH", "0")
    monkeypatch.setenv("ENABLE_VOCAB_ENRICHMENT", "0")
    with app.app_context():
        from database import db

        db.session.add(
            Property(
                title="Plain Title",
                address="1 Rd",
                property_type="house",
                price=1,
                description="UNIQUESECRETWORD renovated loft",
            )
        )
        db.session.commit()
        req = parse_search_request(q="UNIQUESECRETWORD", scope="properties")
        result = unified_search_service.search(req)
        titles = [h["title"] for h in result["groups"].get("properties", [])]
        assert "Plain Title" not in titles


def test_description_searched_when_flag_on(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_DESCRIPTION_SEARCH", "1")
    monkeypatch.setenv("ENABLE_VOCAB_ENRICHMENT", "0")
    with app.app_context():
        from database import db

        db.session.add(
            Property(
                title="Plain Title Two",
                address="2 Rd",
                property_type="house",
                price=1,
                description="UNIQUESECRETWORD2 renovated loft",
            )
        )
        db.session.commit()
        req = parse_search_request(q="UNIQUESECRETWORD2", scope="properties")
        result = unified_search_service.search(req)
        titles = [h["title"] for h in result["groups"].get("properties", [])]
        assert "Plain Title Two" in titles

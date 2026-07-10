"""Property search synonym expand; flag-off baseline; customers unaffected."""

import os

from services.unified_search import parse_search_request, unified_search_service
from services.vocab.lexicon import invalidate_lexicon_cache
from services.vocab.service import vocab_service
from sqlalchemy_models import Customer, Property


def test_flag_off_no_synonym_expand(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_VOCAB_ENRICHMENT", "0")
    with app.app_context():
        from database import db

        invalidate_lexicon_cache()
        term = vocab_service.create_term("villa")
        vocab_service.add_synonym(term.id, "house")
        db.session.add(
            Property(
                title="Seaside Villa Estate",
                address="1 Sea Rd",
                property_type="villa",
                price=100,
                file_code="FC-VOCAB-1",
            )
        )
        db.session.commit()
        # "house" should NOT match "Villa" when flag off
        req = parse_search_request(q="house", scope="properties")
        result = unified_search_service.search(req)
        titles = [h["title"] for h in result["groups"].get("properties", [])]
        assert "Seaside Villa Estate" not in titles


def test_flag_on_synonym_hits_property(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_VOCAB_ENRICHMENT", "1")
    with app.app_context():
        from database import db

        invalidate_lexicon_cache()
        term = vocab_service.create_term("villa")
        vocab_service.add_synonym(term.id, "house")
        invalidate_lexicon_cache()
        db.session.add(
            Property(
                title="Seaside Villa Estate",
                address="1 Sea Rd",
                property_type="villa",
                price=100,
                file_code="FC-VOCAB-2",
            )
        )
        db.session.commit()
        req = parse_search_request(q="house", scope="properties")
        result = unified_search_service.search(req)
        titles = [h["title"] for h in result["groups"].get("properties", [])]
        assert "Seaside Villa Estate" in titles
        assert result.get("vocab_expanded") is True


def test_customers_not_expanded(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_VOCAB_ENRICHMENT", "1")
    with app.app_context():
        from database import db

        invalidate_lexicon_cache()
        term = vocab_service.create_term("ada")
        vocab_service.add_synonym(term.id, "augusta")
        invalidate_lexicon_cache()
        db.session.add(
            Customer(
                name="Ada Lovelace",
                email="ada-vocab@example.com",
                phone="5552000001",
                status="active",
            )
        )
        db.session.commit()
        # synonym of name fragment must not apply to customers
        req = parse_search_request(q="augusta", scope="customers")
        result = unified_search_service.search(req)
        titles = [h["title"] for h in result["groups"].get("customers", [])]
        assert "Ada Lovelace" not in titles

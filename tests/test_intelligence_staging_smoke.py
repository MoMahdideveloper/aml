"""Automated slice of docs/INTELLIGENCE_STAGING_CHECKLIST.md (flags forced in test)."""

import os

from services.intelligence_settings import FLAG_CATALOG
from services.unified_search import parse_search_request, unified_search_service
from sqlalchemy_models import Property


def test_flag_catalog_has_core_keys():
    keys = {f["key"] for f in FLAG_CATALOG}
    for required in (
        "global_search",
        "vocab_enrichment",
        "hybrid_search",
        "ai_context",
        "ai_answer",
        "derived_edges",
        "search_shadow",
        "description_search",
        "nl_query_parse",
        "vocab_occurrences",
        "customer_nl_filters",
    ):
        assert required in keys


def test_customer_nl_off_does_not_emit_hard_filters(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_CUSTOMER_NL_FILTERS", "0")
    with app.app_context():
        from database import db
        from sqlalchemy_models import Customer

        db.session.add(
            Customer(
                name="Staging Customer",
                email="staging-c@example.com",
                phone="5551110001",
                preferred_bedrooms=2,
                budget_max=400_000,
                preferred_type="apartment",
            )
        )
        db.session.commit()
        req = parse_search_request(
            q="2 bedroom apartment under 500k", scope="customers", mode="full"
        )
        result = unified_search_service.search(req)
        assert not (result.get("customer_nl") or {}).get("hard_filters")


def test_keyword_search_with_intelligence_off(db_setup, app, monkeypatch):
    for env in (
        "ENABLE_HYBRID_SEARCH",
        "ENABLE_VOCAB_ENRICHMENT",
        "ENABLE_AI_CONTEXT",
        "ENABLE_CUSTOMER_NL_FILTERS",
        "ENABLE_NL_QUERY_PARSE",
        "ENABLE_DESCRIPTION_SEARCH",
    ):
        monkeypatch.setenv(env, "0")
    monkeypatch.setenv("ENABLE_GLOBAL_SEARCH", "1")
    with app.app_context():
        from database import db

        p = Property(
            title="Staging Smoke Villa",
            address="1 Test",
            property_type="villa",
            price=100,
            bedrooms=3,
        )
        db.session.add(p)
        db.session.commit()
        req = parse_search_request(q="Staging Smoke", scope="properties", mode="full")
        result = unified_search_service.search(req)
        ids = {h["id"] for h in result["groups"]["properties"]}
        assert p.id in ids
        assert result.get("vocab_expanded") is False


def test_hybrid_degraded_path_when_enabled(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "1")
    monkeypatch.setenv("ENABLE_VOCAB_ENRICHMENT", "0")
    monkeypatch.setenv("ENABLE_NL_QUERY_PARSE", "0")
    with app.app_context():
        from database import db
        from services.hybrid_search import HybridSearchService

        p = Property(
            title="Hybrid Smoke Apartment",
            address="2 Test",
            property_type="apartment",
            price=250_000,
            bedrooms=2,
        )
        db.session.add(p)
        db.session.commit()
        req = parse_search_request(
            q="2 bedroom apartment under 300k", scope="properties", mode="full"
        )
        # Should not raise; may degrade without embeddings
        out = HybridSearchService().search(req)
        assert "groups" in out
        assert "properties" in out["groups"]

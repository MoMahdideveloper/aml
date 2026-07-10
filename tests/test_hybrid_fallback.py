"""Hybrid search degrades to keyword when embeddings unavailable."""

import json

from services.hybrid_search import hybrid_search_service
from services.unified_search import parse_search_request
from sqlalchemy_models import Property, PropertyEmbedding


def test_flag_off_passthrough(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "0")
    with app.app_context():
        from database import db

        db.session.add(
            Property(
                title="Ocean Villa",
                address="1 Beach",
                property_type="villa",
                price=100,
                bedrooms=3,
            )
        )
        db.session.commit()
        req = parse_search_request(q="Ocean", scope="properties", mode="full")
        result = hybrid_search_service.search(req)
        assert result["hybrid"]["enabled"] is False
        assert result["total_count"] >= 1


def test_semantic_missing_degrades(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "1")
    with app.app_context():
        from database import db

        db.session.add(
            Property(
                title="Mountain House",
                address="2 Peak",
                property_type="house",
                price=200,
                bedrooms=2,
            )
        )
        db.session.commit()
        # no PropertyEmbedding rows
        req = parse_search_request(q="Mountain", scope="properties", mode="full")
        result = hybrid_search_service.search(req)
        assert result["hybrid"]["enabled"] is True
        assert result["hybrid"]["mode"] == "keyword_only"
        assert result["hybrid"]["degraded"] is True
        titles = [h["title"] for h in result["groups"]["properties"]]
        assert "Mountain House" in titles


def test_hard_filter_beds(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "1")
    with app.app_context():
        from database import db

        db.session.add(
            Property(
                title="Tiny Flat",
                address="A",
                property_type="apartment",
                price=100,
                bedrooms=1,
            )
        )
        db.session.add(
            Property(
                title="Big Flat",
                address="B",
                property_type="apartment",
                price=100,
                bedrooms=4,
            )
        )
        db.session.commit()
        req = parse_search_request(q="3 bedroom apartment", scope="properties", mode="full")
        result = hybrid_search_service.search(req)
        titles = [h["title"] for h in result["groups"]["properties"]]
        assert "Big Flat" in titles
        assert "Tiny Flat" not in titles
        assert any("Bedrooms" in c for c in result["hybrid"].get("chips", []))


def test_hybrid_with_embeddings(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "1")
    with app.app_context():
        from database import db

        p = Property(
            title="Luxury Waterfront",
            address="Dock 9",
            property_type="villa",
            price=900,
            bedrooms=5,
        )
        db.session.add(p)
        db.session.flush()
        # deterministic embedding that will match hash-fallback embed of query somewhat
        # use same hash path: store a non-empty vector
        vec = [0.1] * 32 + [0.0] * 32
        db.session.add(
            PropertyEmbedding(
                property_id=p.id,
                embedding_data=json.dumps(vec),
                source_hash="test",
                provider="test",
                dimension=len(vec),
            )
        )
        db.session.commit()

        # force embed to return same vector for positive similarity
        import services.hybrid_search as hs

        monkeypatch.setattr(
            hs,
            "_embed_query",
            lambda text: (vec, False, "ok"),
        )
        req = parse_search_request(q="Luxury", scope="properties", mode="full")
        result = hybrid_search_service.search(req)
        assert result["hybrid"]["mode"] == "hybrid"
        assert result["hybrid"]["degraded"] is False
        assert result["groups"]["properties"]

from types import SimpleNamespace

import pytest

import services.search_service as search_module
from services.search_service import SearchService


def _property(property_id: int, price: int, rating: float) -> SimpleNamespace:
    return SimpleNamespace(
        id=property_id,
        title=f"Property {property_id}",
        address=f"{property_id} Test Street",
        price=price,
        property_type="house",
        bedrooms=3,
        bathrooms=2,
        neighborhood="downtown",
        status="active",
        is_deleted=False,
        rating=rating,
    )


def _customer() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        budget_min=0,
        budget_max=0,
        preferred_bedrooms=0,
        preferred_bathrooms=0,
        preferred_type="",
        location_preference="",
    )


def test_keyword_only_mode_is_deterministic(monkeypatch):
    properties = [
        _property(property_id=1, price=500_000, rating=4.0),
        _property(property_id=2, price=700_000, rating=5.0),
        _property(property_id=3, price=600_000, rating=5.0),
    ]

    monkeypatch.setattr(search_module.database_service, "get_properties", lambda **_: properties)

    class _VectorFallback:
        @staticmethod
        def search_properties_with_meta(*_, **__):
            return {
                "results": [],
                "meta": {
                    "mode": "rule_fallback",
                    "is_fallback": True,
                    "reason": "vector_backend_down",
                },
            }

    monkeypatch.setattr(search_module, "vector_service", _VectorFallback())

    service = SearchService()
    bundle = service.search_properties_with_meta(customer=_customer(), top_k=3)

    assert bundle["meta"]["mode"] == "keyword_only"
    assert bundle["meta"]["is_fallback"] is True
    assert bundle["meta"]["fallback_reason"] == "vector_backend_down"
    assert [item["property"].id for item in bundle["results"]] == [3, 2, 1]


def test_hybrid_mode_uses_weighted_semantic_keyword_scores(monkeypatch):
    properties = [
        _property(property_id=10, price=450_000, rating=4.5),
        _property(property_id=11, price=470_000, rating=4.5),
    ]

    monkeypatch.setattr(search_module.database_service, "get_properties", lambda **_: properties)

    class _VectorHybrid:
        @staticmethod
        def search_properties_with_meta(*_, **__):
            return {
                "results": [
                    {"property": properties[0], "semantic_score": 100.0},
                    {"property": properties[1], "semantic_score": 0.0},
                ],
                "meta": {
                    "mode": "semantic_hybrid",
                    "is_fallback": False,
                    "reason": None,
                },
            }

    monkeypatch.setattr(search_module, "vector_service", _VectorHybrid())

    service = SearchService()
    bundle = service.search_properties_with_meta(customer=_customer(), top_k=2)

    assert bundle["meta"]["mode"] == "hybrid"
    assert bundle["meta"]["is_fallback"] is False

    score_by_id = {
        item["property"].id: item["hybrid_score"]
        for item in bundle["results"]
    }
    assert score_by_id[10] == pytest.approx(85.0)
    assert score_by_id[11] == pytest.approx(15.0)
    assert [item["property"].id for item in bundle["results"]] == [10, 11]

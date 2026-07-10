"""Search intent interpreter."""

from services.search_intent import detect_scopes, interpret_query


def test_interpret_hard_filters():
    intent = interpret_query("3 bedroom apartment under 500k near downtown")
    assert intent.hard_filters.get("bedrooms_min") == 3
    assert intent.hard_filters.get("price_max") == 500_000
    assert intent.hard_filters.get("property_type") == "apartment"
    pub = intent.to_public_dict()
    assert "raw_query" not in pub


def test_detect_scopes_customers():
    scopes = detect_scopes("find customers looking for villas")
    assert "customers" in scopes

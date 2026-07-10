"""Rule-based query constraint extract."""

from services.query_constraints import extract_constraints, property_matches_hard
from types import SimpleNamespace


def test_beds_and_type():
    c = extract_constraints("3 bedroom villa under 500k")
    assert c.bedrooms_min == 3
    assert c.confidences["bedrooms_min"] >= 0.8
    assert c.property_type == "villa"
    assert c.price_max == 500_000
    hard = c.hard_filters()
    assert hard["bedrooms_min"] == 3
    assert hard["price_max"] == 500_000


def test_for_rent_high_confidence():
    c = extract_constraints("apartment for rent")
    assert c.listing_type == "rental"
    assert c.property_type == "apartment"
    assert "listing_type" in c.hard_filters()



def test_property_matches_hard():
    prop = SimpleNamespace(
        property_type="villa",
        bedrooms=4,
        price=400_000,
        listing_type="sale",
    )
    assert property_matches_hard(prop, {"bedrooms_min": 3, "price_max": 500_000})
    assert not property_matches_hard(prop, {"bedrooms_min": 5})
    assert not property_matches_hard(prop, {"price_max": 100_000})


def test_empty_query():
    c = extract_constraints("")
    assert c.hard_filters() == {}

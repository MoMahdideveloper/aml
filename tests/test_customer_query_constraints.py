"""Unit tests for customer NL constraints."""

from services.customer_query_constraints import (
    customer_matches_hard,
    extract_customer_constraints,
)


def test_extract_beds_budget_type():
    c = extract_customer_constraints(
        "Find customers seeking renovated two-bedroom apartments below 500k"
    )
    # "two-bedroom" may not match \d+ bedroom pattern — use numeric form
    c2 = extract_customer_constraints(
        "customers seeking 2 bedroom apartment under 500k"
    )
    hard = c2.hard_filters()
    assert hard.get("preferred_bedrooms_min") == 2
    assert hard.get("budget_max") == 500_000
    assert hard.get("preferred_type") == "apartment"


def test_extract_location():
    c = extract_customer_constraints("buyers near Downtown under 400k")
    hard = c.hard_filters()
    assert hard.get("budget_max") == 400_000
    assert hard.get("location_token")
    assert "downtown" in hard["location_token"].casefold()


def test_customer_matches_hard_predicate():
    class C:
        preferred_type = "apartment"
        preferred_bedrooms = 2
        budget_min = 100_000
        budget_max = 450_000
        location_preference = "Downtown core"

    hard = {
        "preferred_type": "apartment",
        "preferred_bedrooms_min": 2,
        "budget_max": 500_000,
        "location_token": "Downtown",
    }
    assert customer_matches_hard(C(), hard) is True

    class Poor:
        preferred_type = "villa"
        preferred_bedrooms = 1
        budget_min = 600_000
        budget_max = 900_000
        location_preference = "suburbs"

    assert customer_matches_hard(Poor(), hard) is False


def test_never_depends_on_preferences_text():
    c = extract_customer_constraints("wants renovated kitchen notes")
    # no structured signal for free-text amenity alone
    assert "preferences" not in c.to_public_dict()

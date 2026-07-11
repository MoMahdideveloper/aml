"""Customer NL structured filters via ENABLE_CUSTOMER_NL_FILTERS."""

from services.unified_search import parse_search_request, unified_search_service
from sqlalchemy_models import Customer


def _seed(db):
    good = Customer(
        name="NL Good Buyer",
        email="nl-good@example.com",
        phone="5557000001",
        status="active",
        preferred_type="apartment",
        preferred_bedrooms=2,
        budget_min=200_000,
        budget_max=480_000,
        location_preference="Downtown",
        preferences="SECRET NOTE SHOULD NOT MATTER renovated penthouse yacht",
    )
    rich = Customer(
        name="NL Rich Buyer",
        email="nl-rich@example.com",
        phone="5557000002",
        status="active",
        preferred_type="apartment",
        preferred_bedrooms=2,
        budget_min=600_000,
        budget_max=1_200_000,
        location_preference="Downtown",
    )
    beds = Customer(
        name="NL Studio Seeker",
        email="nl-studio@example.com",
        phone="5557000003",
        status="active",
        preferred_type="apartment",
        preferred_bedrooms=0,
        budget_min=100_000,
        budget_max=300_000,
        location_preference="Downtown",
    )
    deleted = Customer(
        name="NL Deleted",
        email="nl-del@example.com",
        phone="5557000004",
        status="active",
        preferred_type="apartment",
        preferred_bedrooms=2,
        budget_min=100_000,
        budget_max=400_000,
        is_deleted=True,
    )
    db.session.add_all([good, rich, beds, deleted])
    db.session.commit()
    return good, rich, beds, deleted


def test_customer_nl_flag_off_ignores_structured_only(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_CUSTOMER_NL_FILTERS", "0")
    with app.app_context():
        from database import db

        _seed(db)
        req = parse_search_request(
            q="2 bedroom apartment under 500k", scope="customers", mode="full"
        )
        result = unified_search_service.search(req)
        assert "customer_nl" not in result or not result.get("customer_nl", {}).get(
            "hard_filters"
        )


def test_customer_nl_hard_filters_sql(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_CUSTOMER_NL_FILTERS", "1")
    with app.app_context():
        from database import db

        good, rich, beds, deleted = _seed(db)
        req = parse_search_request(
            q="customers seeking 2 bedroom apartment under 500k",
            scope="customers",
            mode="full",
        )
        result = unified_search_service.search(req)
        assert "customer_nl" in result
        hard = result["customer_nl"]["hard_filters"]
        assert hard.get("preferred_bedrooms_min") == 2
        assert hard.get("budget_max") == 500_000
        ids = {h["id"] for h in result["groups"]["customers"]}
        assert good.id in ids
        assert rich.id not in ids
        assert beds.id not in ids
        assert deleted.id not in ids
        # chips explain without raw secret preferences
        chips = " ".join(result["customer_nl"].get("chips") or [])
        assert "SECRET" not in chips
        assert "yacht" not in chips


def test_customer_name_keyword_still_works_flag_on(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_CUSTOMER_NL_FILTERS", "1")
    with app.app_context():
        from database import db

        good, _, _, _ = _seed(db)
        req = parse_search_request(q="NL Good", scope="customers", mode="full")
        result = unified_search_service.search(req)
        ids = {h["id"] for h in result["groups"]["customers"]}
        assert good.id in ids

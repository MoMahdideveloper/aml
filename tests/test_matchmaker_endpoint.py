import json

from database import db
from sqlalchemy_models import Agent, Customer, Property, PropertyFavorite


def _seed_matchmaker_data():
    agent = Agent(
        name="Match Agent",
        email="match.agent@example.com",
        phone="555-7100",
        specialization="Residential",
    )
    customer = Customer(
        name="Sarah Buyer",
        email="sarah.buyer@example.com",
        phone="555-7101",
        budget_min=300000,
        budget_max=600000,
        preferred_bedrooms=2,
        preferred_bathrooms=2,
        preferred_type="apartment",
        location_preference="Downtown",
        status="active",
        preferences=json.dumps({"ai_profile": {"is_real_seller": True, "urgency": "high"}}),
    )
    property_top = Property(
        title="Ground Floor Downtown Condo",
        address="10 Main St",
        price=450000,
        property_type="apartment",
        bedrooms=2,
        bathrooms=2,
        square_feet=130,
        neighborhood="Downtown",
        status="active",
        property_condition="good",
        custom_fields=json.dumps(
            {
                "smart_benefits": [{"feature": "Floor 1", "benefit": "Easy access for groceries and pets."}],
                "trending_badges": ["Low Maintenance"],
            }
        ),
    )
    property_other = Property(
        title="Suburban Villa",
        address="99 Hill Rd",
        price=850000,
        property_type="house",
        bedrooms=4,
        bathrooms=3,
        square_feet=300,
        neighborhood="Suburbs",
        status="active",
        property_condition="good",
    )

    db.session.add_all([agent, customer, property_top, property_other])
    db.session.commit()

    # Boost top property demand score with recent favorites.
    favorites = [PropertyFavorite(property_id=property_top.id, user_id=index + 1) for index in range(20)]
    db.session.add_all(favorites)
    db.session.commit()

    return customer.id, property_top.id


def test_matchmaker_requires_session(client):
    response = client.post(
        "/api/v1/copilot/matchmaker/1",
        json={},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"] == "unauthorized"


def test_matchmaker_returns_ranked_matches_and_sms(client, app, db_setup):
    with app.app_context():
        customer_id, property_id = _seed_matchmaker_data()

    with client.session_transaction() as session:
        session["user_id"] = 1001

    response = client.post(
        f"/api/v1/copilot/matchmaker/{customer_id}",
        json={"max_results": 3, "min_property_score": 50},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["customer_id"] == customer_id
    assert isinstance(payload["customer_score"], int)
    assert payload["customer_badge"] in {"Hot Lead", "Warm Lead", "Browsing"}
    assert payload["matches"], "Expected at least one match"
    assert payload["top_match"]["property_id"] == property_id
    assert payload["top_match"]["match_score"] >= 50
    assert isinstance(payload["sms_draft"], str) and payload["sms_draft"].strip()

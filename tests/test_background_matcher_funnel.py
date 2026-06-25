from unittest.mock import patch

from background_matcher import background_matcher
from database import db
from sqlalchemy_models import Customer, Property


def test_matcher_calls_gemini_per_customer_not_cross_product(app, db_setup):
    with app.app_context():
        customers = []
        for idx in range(3):
            customer = Customer(
                name=f"Customer {idx}",
                email=f"customer{idx}@example.com",
                phone=f"555000{idx}",
                budget_min=100000,
                budget_max=400000,
                preferred_bedrooms=2,
                preferred_bathrooms=1,
                preferred_type="house",
                status="active",
            )
            db.session.add(customer)
            customers.append(customer)

        properties = []
        for idx in range(12):
            prop = Property(
                title=f"Property {idx}",
                address=f"{idx} Main St",
                price=150000 + (idx * 5000),
                property_type="house",
                bedrooms=2,
                bathrooms=1,
                square_feet=120,
                description="test",
                status="active",
            )
            db.session.add(prop)
            properties.append(prop)

        db.session.commit()

        mock_ranked = [
            {"property": prop, "hybrid_score": 80.0, "semantic_score": 80.0, "match_reasons": []}
            for prop in properties[:5]
        ]

        with patch("background_matcher.vector_service.search_properties", return_value=mock_ranked):
            with patch("background_matcher.gemini_service.get_property_recommendations", return_value=[] ) as mocked_gemini:
                background_matcher.find_property_matches(batch_size=50)
                assert mocked_gemini.call_count == len(customers)


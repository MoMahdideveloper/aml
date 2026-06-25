from database import db
from services import search_service as search_module
from services.search_service import execute_property_search
from sqlalchemy_models import Agent, Property


def test_execute_property_search_merges_external_results(app, db_setup, monkeypatch):
    with app.app_context():
        agent = Agent(
            name="Merge Agent",
            email="merge.agent@example.com",
            phone="555-5500",
            specialization="Residential",
        )
        db.session.add(agent)
        db.session.commit()

        local_property = Property(
            title="Local Apartment",
            address="100 Local St",
            price=400000,
            property_type="apartment",
            bedrooms=2,
            bathrooms=2,
            square_feet=125,
            neighborhood="Downtown",
            status="active",
            agent_id=agent.id,
        )
        db.session.add(local_property)
        db.session.commit()

        class _DummyExternal:
            is_enabled = True

            @staticmethod
            def search_properties(**kwargs):
                return [
                    {
                        "external_code": "9001",
                        "id": None,
                        "title": "External Apartment",
                        "property_type": "apartment",
                        "listing_type": "sale",
                        "price": 420000,
                        "bedrooms": 2,
                        "bathrooms": 2,
                        "square_feet": 130,
                        "neighborhood": "Downtown",
                        "description": "External listing",
                        "source": "maskan_live_api",
                    }
                ]

        monkeypatch.setattr(search_module, "maskan_live_service", _DummyExternal())

        rows = execute_property_search(beds=2, sqm=120, top_k=5)
        titles = [row["title"] for row in rows]
        assert "Local Apartment" in titles
        assert "External Apartment" in titles

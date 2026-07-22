"""Integration coverage for the automatic rematch queue and matcher path."""

from unittest.mock import patch

from database import db
from services.scheduler_service import process_rematch_queue_job
from sqlalchemy_models import Agent, Customer, Property, PropertyMatch, RematchQueue


def test_rematch_queue_drives_matching_cycle(app, db_setup):
    """ORM mutations enqueue work that drains into a persisted property match."""
    with app.app_context():
        agent = Agent(
            name="Integration Agent",
            email="integration-agent@example.com",
            phone="+10000000001",
        )
        customer = Customer(
            name="Integration Buyer",
            email="integration-buyer@example.com",
            phone="+10000000002",
            budget_min=100000,
            budget_max=200000,
            preferred_bedrooms=3,
            preferred_type="house",
            status="active",
        )
        db_setup.session.add_all([agent, customer])
        db_setup.session.flush()

        property_obj = Property(
            title="Integration House",
            address="1 Integration Street",
            price=150000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1200,
            description="A deterministic integration-test listing",
            agent_id=agent.id,
            status="active",
        )
        db_setup.session.add(property_obj)
        db_setup.session.commit()

        queued = RematchQueue.query.filter(
            RematchQueue.dedupe_key.in_(
                [f"property:{property_obj.id}", f"customer:{customer.id}"]
            ),
            RematchQueue.status == "pending",
        ).all()
        assert {row.dedupe_key for row in queued} == {
            f"property:{property_obj.id}",
            f"customer:{customer.id}",
        }

        recommendation = {
            "property": property_obj,
            "property_id": property_obj.id,
            "customer_id": customer.id,
            "match_score": 85,
            "analysis": "Strong budget, type, and bedroom fit",
        }

        with patch("background_matcher.gemini_service") as mock_gemini:
            mock_gemini.get_property_recommendations.return_value = [recommendation]
            process_rematch_queue_job()

        mock_gemini.get_property_recommendations.assert_called()
        db_setup.session.expire_all()

        rows = RematchQueue.query.filter(
            RematchQueue.dedupe_key.in_(
                [f"property:{property_obj.id}", f"customer:{customer.id}"]
            )
        ).all()
        assert {row.status for row in rows} == {"done"}

        matches = PropertyMatch.query.filter_by(
            property_id=property_obj.id,
            customer_id=customer.id,
        ).all()
        assert len(matches) == 1
        assert matches[0].match_score >= 0.8

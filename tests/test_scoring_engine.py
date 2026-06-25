from database import db
from services.proptech_scoring import (
    compute_and_cache_scores,
    get_customer_score,
    get_property_score,
    rank_properties_for_customer,
)
from sqlalchemy_models import Agent, Customer, Property
from tasks.scoring_engine import run_nightly_scoring_job


def _seed_entities():
    agent = Agent(
        name="Score Agent",
        email="score.agent@example.com",
        phone="555-4200",
        specialization="Residential",
    )
    customer = Customer(
        name="Score Customer",
        email="score.customer@example.com",
        phone="555-4201",
        budget_min=200000,
        budget_max=500000,
        preferred_bedrooms=2,
        preferred_bathrooms=2,
        preferred_type="apartment",
        location_preference="Downtown",
        status="active",
        preferences="pre-approved buyer, urgent timeline",
    )
    property_obj = Property(
        title="Score Condo",
        address="1 Score Lane",
        price=350000,
        property_type="apartment",
        bedrooms=2,
        bathrooms=2,
        square_feet=120,
        neighborhood="Downtown",
        status="active",
        property_condition="good",
        agent=agent,
    )
    db.session.add_all([agent, customer, property_obj])
    db.session.commit()
    return customer, property_obj


def test_compute_and_cache_scores_produces_counts(app, db_setup):
    with app.app_context():
        customer, property_obj = _seed_entities()
        result = compute_and_cache_scores()

        assert result["customers_processed"] >= 1
        assert result["properties_processed"] >= 1
        assert 0 <= get_customer_score(customer) <= 100
        assert 0 <= get_property_score(property_obj) <= 100


def test_rank_properties_for_customer_returns_scored_matches(app, db_setup):
    with app.app_context():
        customer, _ = _seed_entities()
        matches = rank_properties_for_customer(customer, max_results=3, min_property_score=0)

        assert matches
        assert matches[0]["match_score"] >= 0
        assert matches[0]["property_score"] >= 0


def test_run_nightly_scoring_job_returns_summary(app, db_setup):
    with app.app_context():
        _seed_entities()
        result = run_nightly_scoring_job()

        assert result["customers_processed"] >= 1
        assert result["properties_processed"] >= 1
        assert "started_at" in result
        assert "finished_at" in result

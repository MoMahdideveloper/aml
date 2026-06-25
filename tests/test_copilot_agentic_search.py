from datetime import datetime

from database import db
from services.search_service import (
    execute_agent_search,
    execute_customer_search,
    execute_deal_search,
    execute_property_search,
    execute_task_search,
)
from sqlalchemy_models import Agent, Customer, Deal, Property, Task


def _seed_agent() -> Agent:
    agent = Agent(
        name="Copilot Agent",
        email="copilot.agent@example.com",
        phone="555-8800",
        specialization="Residential",
    )
    db.session.add(agent)
    db.session.commit()
    return agent


def test_execute_property_search_applies_numeric_and_location_filters(app, db_setup):
    with app.app_context():
        agent = _seed_agent()

        p1 = Property(
            title="Downtown Two Bed",
            address="100 Main St",
            price=420000,
            property_type="apartment",
            bedrooms=2,
            bathrooms=2,
            square_feet=130,
            neighborhood="Downtown",
            status="active",
            agent_id=agent.id,
        )
        p2 = Property(
            title="Suburb Family Home",
            address="200 Oak Ave",
            price=550000,
            property_type="house",
            bedrooms=4,
            bathrooms=3,
            square_feet=220,
            neighborhood="Suburbs",
            status="active",
            agent_id=agent.id,
        )
        p3 = Property(
            title="Too Small",
            address="300 Pine Rd",
            price=300000,
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            square_feet=90,
            neighborhood="Downtown",
            status="active",
            agent_id=agent.id,
        )
        p4 = Property(
            title="Deleted Match",
            address="400 River St",
            price=410000,
            property_type="apartment",
            bedrooms=2,
            bathrooms=2,
            square_feet=140,
            neighborhood="Downtown",
            status="active",
            is_deleted=True,
            agent_id=agent.id,
        )

        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        results = execute_property_search(
            beds=2,
            sqm=120,
            max_price=500000,
            property_type="apartment",
            location="Downtown",
            top_k=10,
        )

        assert len(results) == 1
        assert results[0]["title"] == "Downtown Two Bed"


def test_execute_customer_search_filters_leads_by_budget_beds_and_location(app, db_setup):
    with app.app_context():
        c1 = Customer(
            name="High Intent Buyer",
            email="high.intent@example.com",
            phone="555-2211",
            budget_min=300000,
            budget_max=650000,
            preferred_bedrooms=2,
            preferred_bathrooms=2,
            preferred_type="apartment",
            location_preference="Downtown",
            status="active",
        )
        c2 = Customer(
            name="Lower Budget Buyer",
            email="lower.intent@example.com",
            phone="555-2212",
            budget_min=100000,
            budget_max=250000,
            preferred_bedrooms=1,
            preferred_bathrooms=1,
            preferred_type="studio",
            location_preference="Suburbs",
            status="active",
        )
        c3 = Customer(
            name="Deleted Buyer",
            email="deleted.intent@example.com",
            phone="555-2213",
            budget_min=300000,
            budget_max=700000,
            preferred_bedrooms=2,
            preferred_bathrooms=2,
            preferred_type="apartment",
            location_preference="Downtown",
            status="active",
            is_deleted=True,
        )

        db.session.add_all([c1, c2, c3])
        db.session.commit()

        results = execute_customer_search(
            min_budget=500000,
            preferred_beds=2,
            location="Downtown",
            top_k=10,
        )

        assert len(results) == 1
        assert results[0]["name"] == "High Intent Buyer"
        assert results[0]["priority_hint"] in {"normal", "medium", "high"}


def test_chat_copilot_requires_session_for_json_api(client):
    response = client.post(
        "/api/v1/chat/copilot",
        json={"message": "find 2 bed properties"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"] == "unauthorized"


def test_chat_copilot_validates_message_payload(client):
    with client.session_transaction() as session:
        session["user_id"] = 123

    response = client.post(
        "/api/v1/chat/copilot",
        json={"message": "   ", "history": []},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "invalid_request"


def test_execute_deal_search_filters_by_status_amount_and_relations(app, db_setup):
    with app.app_context():
        agent = _seed_agent()
        customer = Customer(
            name="Deal Buyer",
            email="deal.buyer@example.com",
            phone="555-3010",
            budget_min=200000,
            budget_max=600000,
            preferred_bedrooms=2,
            preferred_bathrooms=2,
            preferred_type="apartment",
            location_preference="Downtown",
            status="active",
        )
        property_obj = Property(
            title="Deal Condo",
            address="500 Deal St",
            price=450000,
            property_type="apartment",
            bedrooms=2,
            bathrooms=2,
            square_feet=120,
            neighborhood="Downtown",
            status="active",
            agent_id=agent.id,
        )
        db.session.add_all([customer, property_obj])
        db.session.commit()

        d1 = Deal(
            status="qualified",
            offer_amount=480000,
            notes="urgent close this week",
            property_id=property_obj.id,
            customer_id=customer.id,
            agent_id=agent.id,
        )
        d2 = Deal(
            status="prospecting",
            offer_amount=250000,
            notes="long term lead",
            property_id=property_obj.id,
            customer_id=customer.id,
            agent_id=agent.id,
        )
        db.session.add_all([d1, d2])
        db.session.commit()

        results = execute_deal_search(
            status="qualified",
            min_offer=400000,
            customer_name="Deal Buyer",
            property_title="Deal Condo",
            agent_name="Copilot Agent",
            top_k=10,
        )

        assert len(results) == 1
        assert results[0]["status"] == "qualified"
        assert results[0]["offer_amount"] == 480000


def test_execute_task_search_filters_by_status_priority_due_and_agent(app, db_setup):
    with app.app_context():
        agent = _seed_agent()
        t1 = Task(
            title="Follow up qualified lead",
            description="Call customer and schedule meeting",
            priority="high",
            status="pending",
            due_date=datetime.fromisoformat("2026-03-05T10:00:00"),
            agent_id=agent.id,
        )
        t2 = Task(
            title="Archive old task",
            description="not urgent",
            priority="low",
            status="completed",
            due_date=datetime.fromisoformat("2026-02-01T10:00:00"),
            agent_id=agent.id,
        )
        db.session.add_all([t1, t2])
        db.session.commit()

        results = execute_task_search(
            status="pending",
            priority="high",
            agent_name="Copilot Agent",
            due_before="2026-03-10",
            due_after="2026-03-01",
            keyword="schedule",
            top_k=10,
        )

        assert len(results) == 1
        assert results[0]["title"] == "Follow up qualified lead"


def test_execute_agent_search_filters_by_metrics_and_specialization(app, db_setup):
    with app.app_context():
        a1 = Agent(
            name="Senior Agent",
            email="senior.agent@example.com",
            phone="555-9991",
            specialization="Luxury Homes",
            total_sales=50,
            active_listings=12,
        )
        a2 = Agent(
            name="Junior Agent",
            email="junior.agent@example.com",
            phone="555-9992",
            specialization="Rentals",
            total_sales=4,
            active_listings=2,
        )
        db.session.add_all([a1, a2])
        db.session.commit()

        results = execute_agent_search(
            specialization="Luxury",
            min_total_sales=20,
            min_active_listings=5,
            top_k=10,
        )

        assert len(results) == 1
        assert results[0]["name"] == "Senior Agent"


def test_execute_property_search_keyword_and_enhanced_filters(app, db_setup):
    """Verifies keyword search, boolean amenities, listing type, and parking filters."""
    with app.app_context():
        agent = _seed_agent()

        p1 = Property(
            title="باغ ویلا لوکس شمال",
            address="جاده نور، مازندران",
            price=8_000_000_000,
            property_type="villa",
            bedrooms=4,
            bathrooms=3,
            square_feet=500,
            neighborhood="نور",
            listing_type="sale",
            parking_spaces=2,
            has_elevator=False,
            has_storage=True,
            status="active",
            agent_id=agent.id,
        )
        p2 = Property(
            title="آپارتمان نوساز با آسانسور",
            address="خیابان آزادی، تهران",
            price=3_500_000_000,
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            square_feet=85,
            neighborhood="آزادی",
            listing_type="sale",
            parking_spaces=1,
            has_elevator=True,
            has_storage=True,
            status="active",
            agent_id=agent.id,
        )
        p3 = Property(
            title="واحد اجاره‌ای مرکز شهر",
            address="خیابان ولیعصر، تهران",
            price=0,
            property_type="apartment",
            bedrooms=1,
            bathrooms=1,
            square_feet=65,
            neighborhood="ولیعصر",
            listing_type="rental",
            rahn=500_000_000,
            ejare=15_000_000,
            has_elevator=True,
            has_storage=False,
            status="active",
            agent_id=agent.id,
        )

        db.session.add_all([p1, p2, p3])
        db.session.commit()

        # ── Keyword search by title ──
        results = execute_property_search(keyword="باغ ویلا")
        assert len(results) == 1
        assert results[0]["title"] == "باغ ویلا لوکس شمال"

        # ── Boolean: elevator filter ──
        results = execute_property_search(has_elevator=True)
        assert len(results) == 2
        titles = {r["title"] for r in results}
        assert "آپارتمان نوساز با آسانسور" in titles
        assert "واحد اجاره‌ای مرکز شهر" in titles

        # ── Boolean: storage filter ──
        results = execute_property_search(has_storage=True)
        assert len(results) == 2

        # ── Listing type filter ──
        results = execute_property_search(listing_type="rental")
        assert len(results) == 1
        assert results[0]["listing_type"] == "rental"

        # ── Parking filter ──
        results = execute_property_search(min_parking=2)
        assert len(results) == 1
        assert results[0]["title"] == "باغ ویلا لوکس شمال"

        # ── Location searches address too ──
        results = execute_property_search(location="ولیعصر")
        assert len(results) == 1
        assert results[0]["title"] == "واحد اجاره‌ای مرکز شهر"

        # ── Combined: keyword + elevator ──
        results = execute_property_search(keyword="نوساز", has_elevator=True)
        assert len(results) == 1
        assert results[0]["title"] == "آپارتمان نوساز با آسانسور"

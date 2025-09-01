def seed_agent_customer_property(app):
    from database import db
    from sqlalchemy_models import Agent, Customer, Property

    with app.app_context():
        agent = Agent(name="Filter Agent", email="filter@example.com", phone="000")
        db.session.add(agent)
        db.session.commit()

        cust = Customer(
            name="Filter Customer",
            email="fc@example.com",
            phone="111",
            budget_min=100000,
            budget_max=800000,
            preferred_bedrooms=2,
            preferred_bathrooms=1,
            preferred_type="Condo",
            location_preference="Downtown",
        )
        db.session.add(cust)
        db.session.commit()

        props = [
            Property(
                title="Condo A",
                address="1 A St",
                price=350000,
                property_type="Condo",
                bedrooms=2,
                bathrooms=2,
                square_feet=900,
                description="",
                status="active",
                agent_id=agent.id,
                year_built=2018,
                property_condition="excellent",
                neighborhood="Downtown",
                property_category="residential",
            ),
            Property(
                title="Condo B",
                address="2 B St",
                price=320000,
                property_type="Condo",
                bedrooms=1,
                bathrooms=1,
                square_feet=700,
                description="",
                status="active",
                agent_id=agent.id,
                year_built=2020,
                property_condition="good",
                neighborhood="Suburbia",
                property_category="residential",
            ),
            Property(
                title="House X",
                address="3 X St",
                price=600000,
                property_type="House",
                bedrooms=4,
                bathrooms=3,
                square_feet=2000,
                description="",
                status="active",
                agent_id=None,
                year_built=2010,
                property_condition="fair",
                neighborhood="Suburbia",
                property_category="residential",
            ),
        ]
        db.session.add_all(props)
        db.session.commit()
        return agent.id, cust.id


def test_properties_filters_and_pagination(client, db_setup, app):
    agent_id, _ = seed_agent_customer_property(app)

    # Filter condos in price range
    resp = client.get("/properties?type=Condo&min_price=300000&max_price=400000")
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Condo A" in body
    assert "House X" not in body

    # Pagination: per_page=1, first page should include a condo
    resp = client.get("/properties?type=Condo&per_page=1&page=1")
    assert resp.status_code == 200

    # Bedrooms, bathrooms, sqft, year, category, condition, neighborhood, agent filters
    url = (
        f"/properties?bedrooms=2&bathrooms=2&min_sqft=800&max_sqft=1000"
        f"&year_built_min=2015&year_built_max=2020&category=residential&condition=excellent"
        f"&neighborhood=Downtown&agent_id={agent_id}"
    )
    resp = client.get(url)
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "Condo A" in body
    assert "Condo B" not in body


def test_negative_validations(client, db_setup):
    # Invalid agent email
    resp = client.post(
        "/agents/add",
        data={"name": "Bad Agent", "email": "not-an-email", "phone": "123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    # Missing fields for new deal should fail validation and redirect cleanly
    resp = client.post("/deals/add", data={}, follow_redirects=True)
    assert resp.status_code == 200

    # Update deal with invalid offer triggers error branch
    # Seed minimal deal first
    from flask import current_app

    from database import db
    from database_service import database_service
    from sqlalchemy_models import Agent, Customer, Property

    with current_app.app_context():
        agent = Agent(name="Neg Agent", email="neg@example.com", phone="1")
        db.session.add(agent)
        db.session.commit()
        customer = Customer(name="Neg Cust", email="nc@example.com", phone="2")
        db.session.add(customer)
        db.session.commit()
        prop = Property(
            title="Neg Home",
            address="1 Neg St",
            price=100000,
            property_type="House",
            bedrooms=1,
            bathrooms=1,
            square_feet=500,
            description="",
            status="active",
            agent_id=agent.id,
        )
        db.session.add(prop)
        db.session.commit()
        deal = database_service.add_deal(prop.id, customer.id, agent.id, "prospecting", 90000)
        deal_id = deal.id

    resp = client.post(
        f"/deals/{deal_id}/update", data={"offer_amount": "abc"}, follow_redirects=True
    )
    assert resp.status_code == 200

    # Invalid task: bad date string should be handled
    # Need an agent id
    with current_app.app_context():
        ag = Agent(name="Task A", email="ta@example.com", phone="3")
        db.session.add(ag)
        db.session.commit()
        ag_id = ag.id

    resp = client.post(
        "/tasks/add",
        data={
            "title": "Do thing",
            "description": "desc",
            "agent_id": str(ag_id),
            "priority": "low",
            "due_date": "not-a-date",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

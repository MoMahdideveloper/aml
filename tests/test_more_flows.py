def test_properties_add_sale(client, db_setup, app):
    # Create agent for assignment
    from database import db
    from sqlalchemy_models import Agent

    with app.app_context():
        agent = Agent(name="Prop Agent", email="prop.agent@example.com", phone="111-222")
        db.session.add(agent)
        db.session.commit()
        agent_id = agent.id

    data = {
        "title": "Brand New Condo",
        "address": "500 Market St",
        "property_type": "Condo",
        "bedrooms": 2,
        "bathrooms": 2,
        "square_feet": 900,
        "agent_id": str(agent_id),
        "listing_type": "sale",
        "sale_price": 420000,
    }
    resp = client.post("/properties/add", data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Brand New Condo" in resp.data


def test_properties_add_rental(client, db_setup, app):
    # No agent required
    data = {
        "title": "Cozy Loft",
        "address": "200 Industrial Rd",
        "property_type": "Loft",
        "bedrooms": 1,
        "bathrooms": 1,
        "square_feet": 600,
        "listing_type": "rental",
        "rahn": 400000000,
        "ejare": 2500000,
    }
    resp = client.post("/properties/add", data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Cozy Loft" in resp.data


def test_deal_update_and_task_complete(client, db_setup, app):
    # Seed agent, customer, property, deal and task then update/complete
    from database import db
    from database_service import database_service
    from sqlalchemy_models import Agent, Customer, Property

    with app.app_context():
        agent = Agent(name="Update Agent", email="u.agent@example.com", phone="123")
        db.session.add(agent)
        db.session.commit()

        customer = Customer(
            name="Update Customer",
            email="uc@example.com",
            phone="321",
            budget_min=100000,
            budget_max=700000,
            preferred_bedrooms=2,
            preferred_bathrooms=1,
            preferred_type="Condo",
            location_preference="Downtown",
        )
        db.session.add(customer)
        db.session.commit()

        prop = Property(
            title="Update Condo",
            address="77 Center",
            price=350000,
            property_type="Condo",
            bedrooms=2,
            bathrooms=1,
            square_feet=800,
            description="",
            status="active",
            agent_id=agent.id,
        )
        db.session.add(prop)
        db.session.commit()

        # Add deal via service to get ID easily
        deal = database_service.add_deal(prop.id, customer.id, agent.id, "prospecting", 345000)

        # Add task via service
        task = database_service.add_task(
            "Follow up", "Call client", agent.id, "high", "pending", None
        )

        deal_id, task_id = deal.id, task.id

    # Update deal offer amount
    resp = client.post(
        f"/deals/{deal_id}/update", data={"offer_amount": 360000}, follow_redirects=True
    )
    assert resp.status_code == 200

    # Complete task
    resp = client.post(f"/tasks/{task_id}/complete", follow_redirects=True)
    assert resp.status_code == 200


def test_recommendations_page(client, db_setup):
    resp = client.get("/recommendations")
    assert resp.status_code == 200

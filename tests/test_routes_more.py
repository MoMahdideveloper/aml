def test_agents_list_and_add(client, db_setup, app):
    # GET list
    resp = client.get("/agents")
    assert resp.status_code == 200

    # POST add
    data = {
        "name": "Alice Agent",
        "email": "alice@example.com",
        "phone": "123-456-7890",
        "specialization": "Residential Properties",
        "bio": "Experienced agent",
    }
    resp = client.post("/agents/add", data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Alice Agent" in resp.data


def test_customers_list_and_add(client, db_setup, app):
    # GET list
    resp = client.get("/customers")
    assert resp.status_code == 200

    # POST add
    data = {
        "name": "Bob Buyer",
        "email": "bob@example.com",
        "phone": "555-000-1111",
        "budget_min": 100000,
        "budget_max": 500000,
        "preferred_bedrooms": 3,
        "preferred_bathrooms": 2,
        "preferred_type": "House",
        "location_preference": "Suburbia",
    }
    resp = client.post("/customers/add", data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Bob Buyer" in resp.data


def test_tasks_list_and_add(client, db_setup, app):
    # Need an agent to assign the task to
    from database import db
    from sqlalchemy_models import Agent

    with app.app_context():
        agent = Agent(name="Task Agent", email="task.agent@example.com", phone="999")
        db.session.add(agent)
        db.session.commit()
        agent_id = agent.id

    resp = client.get("/tasks")
    assert resp.status_code == 200

    data = {
        "title": "Call client",
        "description": "Follow up on showing",
        "agent_id": str(agent_id),
        "priority": "high",
        "due_date": "2030-01-01",
    }
    resp = client.post("/tasks/add", data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Call client" in resp.data


def test_deals_list_and_add(client, db_setup, app):
    # Create property, customer, agent
    from database import db
    from sqlalchemy_models import Agent, Customer, Property

    with app.app_context():
        agent = Agent(name="Deal Agent", email="deal.agent@example.com", phone="111")
        db.session.add(agent)
        db.session.commit()

        customer = Customer(
            name="Carl Customer",
            email="carl@example.com",
            phone="555",
            budget_min=100000,
            budget_max=800000,
            preferred_bedrooms=3,
            preferred_bathrooms=2,
            preferred_type="House",
            location_preference="Suburbia",
        )
        db.session.add(customer)
        db.session.commit()

        prop = Property(
            title="Deal Home",
            address="1 Street",
            price=300000,
            property_type="House",
            bedrooms=3,
            bathrooms=2,
            square_feet=1200,
            description="",
            status="active",
            agent_id=agent.id,
        )
        db.session.add(prop)
        db.session.commit()

        prop_id, cust_id, ag_id = prop.id, customer.id, agent.id

    # List
    resp = client.get("/deals")
    assert resp.status_code == 200

    # Add
    data = {
        "property_id": str(prop_id),
        "customer_id": str(cust_id),
        "agent_id": str(ag_id),
        "status": "qualified",
        "offer_amount": 310000,
    }
    resp = client.post("/deals/add", data=data, follow_redirects=True)
    assert resp.status_code == 200

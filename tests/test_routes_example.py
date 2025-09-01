def test_properties_page_lists_inserted_property(client, db_setup, app):
    # Arrange: create minimal agent and property
    from database import db
    from sqlalchemy_models import Agent, Property

    with app.app_context():
        agent = Agent(name="Test Agent", email="agent@example.com", phone="1234567890")
        db.session.add(agent)
        db.session.commit()

        prop = Property(
            title="Sunny Apartment",
            address="123 Main St",
            price=250000,
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            square_feet=800,
            description="Bright and cozy",
            status="active",
            agent_id=agent.id,
        )
        db.session.add(prop)
        db.session.commit()

    # Act
    resp = client.get("/properties")

    # Assert
    assert resp.status_code == 200
    assert b"Sunny Apartment" in resp.data


def test_dashboard_renders_without_data(client, db_setup):
    resp = client.get("/")
    assert resp.status_code == 200

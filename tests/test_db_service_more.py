def test_database_service_crud_and_stats(client, db_setup, app):
    from database import db
    from database_service import database_service
    from sqlalchemy_models import Agent

    with app.app_context():
        # Create agent
        ag = Agent(name="Srv Agent", email="srv.agent@example.com", phone="777")
        db.session.add(ag)
        db.session.commit()

        # Add property via service
        p = database_service.add_property(
            title="Srv Home",
            address="9 Service Rd",
            price=200000,
            property_type="House",
            bedrooms=3,
            bathrooms=2,
            square_feet=1200,
            description="",
            status="active",
            agent_id=ag.id,
            year_built=2015,
            parking_spaces=1,
            floors=1,
            units=1,
            property_condition="good",
            heating_type="",
            cooling_type="",
            rental_price=None,
            property_features="",
            neighborhood="Suburbia",
            property_category="residential",
            listing_type="sale",
            rahn=None,
            ejare=None,
        )
        assert p.id is not None

        # Update property
        updated = database_service.update_property(p.id, price=210000, status="active")
        assert updated.price == 210000

        # Get property and delete it
        got = database_service.get_property(p.id)
        assert got is not None
        deleted = database_service.delete_property(p.id)
        assert deleted is True

        # Add customer
        cust = database_service.add_customer(
            name="Srv Cust",
            email="srv.cust@example.com",
            phone="100",
            budget_min=100000,
            budget_max=300000,
            preferred_bedrooms=2,
            preferred_bathrooms=1,
            preferred_type="House",
            location_preference="Suburbia",
        )
        assert cust.id is not None

        # Get agent and customer by id
        assert database_service.get_agent(ag.id) is not None
        assert database_service.get_customer(cust.id) is not None

        # Add a property again for a deal and task
        p2 = database_service.add_property(
            title="Srv Home 2",
            address="10 Service Rd",
            price=250000,
            property_type="House",
            bedrooms=3,
            bathrooms=2,
            square_feet=1300,
            description="",
            status="active",
            agent_id=ag.id,
        )
        deal = database_service.add_deal(
            p2.id, cust.id, ag.id, status="qualified", offer_amount=240000
        )
        assert database_service.get_deal(deal.id) is not None

        # Tasks filtered and completion
        task = database_service.add_task(
            "Srv Task", "Do it", ag.id, priority="high", status="pending"
        )
        tasks_for_agent = database_service.get_tasks(agent_id=ag.id, status="pending")
        assert any(t.id == task.id for t in tasks_for_agent)
        completed = database_service.complete_task(task.id)
        assert completed is not None and completed.status == "completed"

        # Dashboard stats
        stats = database_service.get_dashboard_stats()
        assert isinstance(stats, dict)
        assert "total_properties" in stats and "total_deals" in stats


def test_get_properties_all_filters_and_edge_cases(client, db_setup, app):
    from database import db
    from database_service import database_service
    from sqlalchemy_models import Agent, Property

    with app.app_context():
        agent = Agent(name="Filter2 Agent", email="f2@example.com", phone="000")
        db.session.add(agent)
        db.session.commit()
        prop = Property(
            title="Edge House",
            address="123 Edge St",
            price=123456,
            property_type="House",
            bedrooms=4,
            bathrooms=3,
            square_feet=1500,
            description="Nice",
            status="active",
            agent_id=agent.id,
            year_built=2012,
            property_condition="good",
            neighborhood="EdgeVille",
            property_category="residential",
        )
        db.session.add(prop)
        db.session.commit()

        # Hit every filter branch
        res = database_service.get_properties(
            search="Edge",
            property_type="House",
            property_category="residential",
            property_condition="good",
            neighborhood="EdgeVille",
            min_price=100000,
            max_price=200000,
            bedrooms=3,
            bathrooms=2,
            min_sqft=1000,
            max_sqft=2000,
            year_built_min=2010,
            year_built_max=2015,
            agent_id=agent.id,
        )
        assert any(p.title == "Edge House" for p in res)

        # Non-existent property and deletion edge
        assert database_service.get_property(999999) is None
        assert database_service.delete_property(999999) is False

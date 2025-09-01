def test_agents_add_exception(monkeypatch, client, db_setup):
    import views.agents as views_agents

    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(views_agents.database_service, "add_agent", boom)

    resp = client.post(
        "/agents/add",
        data={"name": "X", "email": "x@example.com", "phone": "1"},
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_customers_add_exception(monkeypatch, client, db_setup):
    import views.customers as views_customers

    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(views_customers.database_service, "add_customer", boom)

    resp = client.post(
        "/customers/add",
        data={
            "name": "Y",
            "email": "y@example.com",
            "phone": "1",
            "budget_min": 0,
            "budget_max": 1,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_deals_add_and_update_exception(monkeypatch, client, db_setup, app):
    import views.deals as views_deals
    from database import db
    from sqlalchemy_models import Agent, Customer, Property

    # Prepare minimal valid entities
    with app.app_context():
        ag = Agent(name="E1", email="e1@example.com", phone="1")
        db.session.add(ag)
        db.session.commit()
        cu = Customer(name="E2", email="e2@example.com", phone="2")
        db.session.add(cu)
        db.session.commit()
        pr = Property(
            title="E Home",
            address="Z",
            price=1,
            property_type="House",
            bedrooms=1,
            bathrooms=1,
            square_feet=1,
            status="active",
            agent_id=ag.id,
        )
        db.session.add(pr)
        db.session.commit()
        ids = (pr.id, cu.id, ag.id)

    # Force exception on add_deal
    def add_boom(*a, **k):
        raise RuntimeError("db down")

    # Monkeypatch add_deal then restore before seeding a real deal
    orig_add = views_deals.database_service.add_deal
    monkeypatch.setattr(views_deals.database_service, "add_deal", add_boom)
    resp = client.post(
        "/deals/add",
        data={"property_id": ids[0], "customer_id": ids[1], "agent_id": ids[2]},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    # Restore and seed a real deal to update, then force update_deal exception
    with app.app_context():
        # Use service directly to create
        from database_service import database_service

        # restore original add_deal on the shared instance
        views_deals.database_service.add_deal = orig_add
        deal = database_service.add_deal(ids[0], ids[1], ids[2], "prospecting", 1)
        deal_id = deal.id

    def upd_boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(views_deals.database_service, "update_deal", upd_boom)
    resp = client.post(f"/deals/{deal_id}/update", data={"offer_amount": 2}, follow_redirects=True)
    assert resp.status_code == 200


def test_tasks_complete_not_found_and_exception(monkeypatch, client, db_setup):
    import views.tasks as views_tasks

    # Not found branch
    resp = client.post("/tasks/999999/complete", follow_redirects=True)
    assert resp.status_code == 200

    # Exception branch
    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(views_tasks.database_service, "complete_task", boom)
    resp = client.post("/tasks/1/complete", follow_redirects=True)
    assert resp.status_code == 200


def test_dashboard_else_branches(monkeypatch, client):
    import views.main as views_main

    # Stub stats to include deals without related objects and tasks without agent
    class Dummy:
        def __init__(self):
            self.property = None
            self.customer = None
            self.agent = None
            self.status = "unknown"
            self.offer_amount = 0

    class DummyTask:
        def __init__(self):
            self.agent = None
            self.title = "t"
            self.description = "d"
            self.priority = "low"

    def fake_stats():
        return {
            "recent_properties": [],
            "recent_deals": [Dummy()],
            "total_properties": 0,
            "active_properties": 0,
            "total_agents": 0,
            "total_customers": 0,
            "total_deals": 0,
            "active_deals": 0,
            "total_deal_value": 0,
            "active_deal_value": 0,
            "avg_property_price": 0,
        }

    monkeypatch.setattr(views_main.database_service, "get_dashboard_stats", fake_stats)
    monkeypatch.setattr(views_main.database_service, "get_tasks", lambda **k: [DummyTask()])

    resp = client.get("/")
    assert resp.status_code == 200


def test_customers_invalid_form(client, db_setup):
    # Missing required fields should trigger validation branch
    resp = client.post("/customers/add", data={}, follow_redirects=True)
    assert resp.status_code == 200


def test_tasks_invalid_form(client, db_setup):
    resp = client.post("/tasks/add", data={}, follow_redirects=True)
    assert resp.status_code == 200

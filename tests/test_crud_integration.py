"""Focused integration coverage for the current form-based CRUD workflows."""

from services.database_service import database_service


def _seed_agent(app, name="Integration Agent", email="integration-agent@example.com"):
    with app.app_context():
        agent = database_service.add_agent(
            name=name,
            email=email,
            phone="123-456-7890",
            specialization="Residential",
            bio="Integration bio",
        )
        return agent.id


def _seed_customer(app, name="Integration Customer", email="integration-customer@example.com"):
    with app.app_context():
        customer = database_service.add_customer(
            name=name,
            email=email,
            phone="987-654-3210",
            budget_min=100000,
            budget_max=300000,
            preferred_bedrooms=3,
            preferred_type="house",
        )
        return customer.id


def _seed_property(app, agent_id):
    with app.app_context():
        property_obj = database_service.add_property(
            title="Integration Property",
            address="123 Integration St",
            price=200000,
            property_type="house",
            bedrooms=3,
            bathrooms=2,
            square_feet=1500,
            description="Integration property",
            status="active",
            agent_id=agent_id,
        )
        return property_obj.id


def _seed_deal(app, agent_id, customer_id, property_id, status="prospecting"):
    with app.app_context():
        deal = database_service.add_deal(
            property_id=property_id,
            customer_id=customer_id,
            agent_id=agent_id,
            status=status,
            offer_amount=190000,
        )
        return deal.id


def _seed_task(app, agent_id):
    with app.app_context():
        task = database_service.add_task(
            title="Original Task",
            description="Original description",
            agent_id=agent_id,
            priority="low",
            status="pending",
        )
        return task.id


class TestCRUDIntegration:
    """Verify end-to-end persistence through the live route contracts."""

    def test_agent_edit_workflow(self, client, app, db_setup):
        agent_id = _seed_agent(app)

        response = client.post(
            f"/agents/{agent_id}/edit",
            data={
                "name": "Updated Integration Agent",
                "email": "updated-integration@example.com",
                "phone": "555-123-4567",
                "specialization": "Commercial",
                "bio": "Updated bio",
            },
        )

        assert response.status_code == 302
        assert response.location.endswith("/agents")
        data = client.get(f"/api/agents/{agent_id}").get_json()
        assert data["name"] == "Updated Integration Agent"
        assert data["email"] == "updated-integration@example.com"
        assert data["specialization"] == "Commercial"

    def test_customer_delete_blocked_by_active_deal(self, client, app, db_setup):
        agent_id = _seed_agent(app)
        customer_id = _seed_customer(app)
        property_id = _seed_property(app, agent_id)
        deal_id = _seed_deal(app, agent_id, customer_id, property_id, status="negotiation")

        response = client.post(
            f"/customers/{customer_id}/delete",
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"active deals" in response.data
        customer = client.get(f"/api/customers/{customer_id}").get_json()
        deal = client.get(f"/api/deals/{deal_id}").get_json()
        assert customer["is_deleted"] is False
        assert deal["is_deleted"] is False

    def test_customer_delete_without_active_deals_soft_deletes(self, client, app, db_setup):
        customer_id = _seed_customer(app)

        response = client.post(
            f"/customers/{customer_id}/delete",
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"deleted successfully" in response.data
        deleted = client.get(f"/api/customers/{customer_id}")
        assert deleted.status_code == 404
        assert deleted.get_json() == {"error": "Customer not found"}

    def test_deal_note_and_update_workflow(self, client, app, db_setup):
        agent_id = _seed_agent(app)
        customer_id = _seed_customer(app)
        property_id = _seed_property(app, agent_id)
        deal_id = _seed_deal(app, agent_id, customer_id, property_id)

        note_response = client.post(
            f"/deals/{deal_id}/note",
            data={"note": "Follow up with customer"},
        )
        update_response = client.post(
            f"/deals/{deal_id}/update",
            data={"status": "negotiation", "offer_amount": "195000"},
        )

        assert note_response.status_code == 302
        assert update_response.status_code == 302
        deal = client.get(f"/api/deals/{deal_id}").get_json()
        assert deal["status"] == "negotiation"
        assert deal["offer_amount"] == 195000
        assert "Follow up with customer" in deal["notes"]

    def test_task_edit_workflow(self, client, app, db_setup):
        agent_id = _seed_agent(app)
        task_id = _seed_task(app, agent_id)

        response = client.post(
            f"/tasks/{task_id}/edit",
            data={
                "title": "Updated Task",
                "description": "Updated description",
                "agent_id": str(agent_id),
                "priority": "high",
                "due_date": "2026-08-01",
            },
        )

        assert response.status_code == 302
        assert response.location.endswith("/tasks")
        task = client.get(f"/api/tasks/{task_id}").get_json()
        assert task["title"] == "Updated Task"
        assert task["description"] == "Updated description"
        assert task["priority"] == "high"
        assert task["due_date"].startswith("2026-08-01")

    def test_missing_records_redirect_to_list_routes(self, client, app, db_setup):
        responses = [
            client.post("/agents/99999/edit", data={}),
            client.post("/customers/99999/delete"),
            client.post("/deals/99999/note", data={"note": "Missing"}),
            client.post("/tasks/99999/edit", data={}),
        ]

        assert all(response.status_code == 302 for response in responses)
        assert responses[0].location.endswith("/agents")
        assert responses[1].location.endswith("/customers")
        assert responses[2].location.endswith("/deals")
        assert responses[3].location.endswith("/tasks")

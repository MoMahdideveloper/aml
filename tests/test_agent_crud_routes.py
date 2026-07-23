"""Tests for the current agent list, JSON, and form routes."""

from services.database_service import database_service


def _seed_agent(app, *, name="Test Agent", email="test@example.com") -> int:
    """Create an agent and return only its scalar ID after the session closes."""
    with app.app_context():
        agent = database_service.add_agent(
            name=name,
            email=email,
            phone="123-456-7890",
            specialization="Residential",
            bio="Test bio",
        )
        return agent.id


def _agent_json(client, agent_id):
    response = client.get(f"/api/agents/{agent_id}")
    assert response.status_code == 200
    return response.get_json()


class TestAgentCRUDRoutes:
    """Exercise the live form-based agent routes and JSON read endpoint."""

    def test_agents_list_page_loads(self, client, app, db_setup):
        _seed_agent(app)

        response = client.get("/agents")

        assert response.status_code == 200
        assert b"Test Agent" in response.data

    def test_agent_json_api_success(self, client, app, db_setup):
        agent_id = _seed_agent(app)

        data = _agent_json(client, agent_id)

        assert data["id"] == agent_id
        assert data["name"] == "Test Agent"
        assert data["email"] == "test@example.com"
        assert data["phone"] == "123-456-7890"
        assert data["specialization"] == "Residential"
        assert data["bio"] == "Test bio"

    def test_agent_json_api_not_found(self, client, app, db_setup):
        response = client.get("/api/agents/99999")

        assert response.status_code == 404
        assert response.get_json() == {"error": "Agent not found"}

    def test_agent_edit_via_post_persists_changes(self, client, app, db_setup):
        agent_id = _seed_agent(app)

        response = client.post(
            f"/agents/{agent_id}/edit",
            data={
                "name": "Updated Agent",
                "email": "updated@example.com",
                "phone": "987-654-3210",
                "specialization": "Commercial",
                "bio": "Updated bio",
            },
        )

        assert response.status_code == 302
        assert response.location.endswith("/agents")
        updated = _agent_json(client, agent_id)
        assert updated["name"] == "Updated Agent"
        assert updated["email"] == "updated@example.com"
        assert updated["phone"] == "987-654-3210"
        assert updated["specialization"] == "Commercial"
        assert updated["bio"] == "Updated bio"

    def test_invalid_email_is_rejected_without_mutation(self, client, app, db_setup):
        agent_id = _seed_agent(app)
        before = _agent_json(client, agent_id)

        response = client.post(
            f"/agents/{agent_id}/edit",
            data={
                "name": "Should Not Persist",
                "email": "invalid-email",
                "phone": "000",
                "specialization": "Invalid",
                "bio": "Invalid",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Invalid email address" in response.data
        assert _agent_json(client, agent_id) == before

    def test_duplicate_email_is_rejected_without_mutation(self, client, app, db_setup):
        agent_id = _seed_agent(app)
        _seed_agent(app, name="Other Agent", email="other@example.com")
        before = _agent_json(client, agent_id)

        response = client.post(
            f"/agents/{agent_id}/edit",
            data={
                "name": "Should Not Persist",
                "email": "other@example.com",
                "phone": "000",
                "specialization": "Invalid",
                "bio": "Invalid",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"already in use by another agent" in response.data
        assert _agent_json(client, agent_id) == before

    def test_same_email_is_allowed_on_edit(self, client, app, db_setup):
        agent_id = _seed_agent(app)

        response = client.post(
            f"/agents/{agent_id}/edit",
            data={
                "name": "Renamed Agent",
                "email": "test@example.com",
                "phone": "987-654-3210",
                "specialization": "Commercial",
                "bio": "Renamed bio",
            },
        )

        assert response.status_code == 302
        updated = _agent_json(client, agent_id)
        assert updated["name"] == "Renamed Agent"
        assert updated["email"] == "test@example.com"

    def test_agent_delete_via_post_soft_deletes(self, client, app, db_setup):
        agent_id = _seed_agent(app)

        response = client.post(f"/agents/{agent_id}/delete")

        assert response.status_code == 302
        assert response.location.endswith("/agents")
        deleted = client.get(f"/api/agents/{agent_id}")
        assert deleted.status_code == 404
        assert deleted.get_json() == {"error": "Agent not found"}

    def test_agent_edit_missing_agent_redirects(self, client, app, db_setup):
        response = client.post(
            "/agents/99999/edit",
            data={
                "name": "Missing",
                "email": "missing@example.com",
                "phone": "000",
            },
        )

        assert response.status_code == 302
        assert response.location.endswith("/agents")

    def test_agent_delete_missing_agent_redirects(self, client, app, db_setup):
        response = client.post("/agents/99999/delete")

        assert response.status_code == 302
        assert response.location.endswith("/agents")

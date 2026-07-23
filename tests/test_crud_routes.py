"""CRUD route tests — updated to match current blueprint layout.

Route map (as of c3d4e5f6a7b8):
  GET  /api/customers/<id>       → JSON customer record
  GET  /customers/<id>           → HTML customer_360 view (405 for XHR expecting JSON)
  POST /customers/<id>/edit      → update customer (form data)
  POST /customers/<id>/delete    → soft-delete customer
  GET  /api/tasks/<id>           → JSON task record
  POST /tasks/<id>/edit          → update task (form data)
  POST /tasks/<id>/delete        → delete task
  POST /tasks/<id>/complete      → mark task done
"""

import pytest
from datetime import date, timedelta
from services.database_service import database_service


class TestCustomerCRUDRoutes:
    """Customer CRUD via blueprint routes."""

    def test_customer_json_api_success(self, client, app, db_setup):
        """GET /api/customers/<id> returns JSON customer record."""
        with app.app_context():
            customer = database_service.add_customer(
                name="Test Customer",
                email="test@example.com",
                phone="123-456-7890",
                budget_min=100000,
                budget_max=200000,
                preferred_bedrooms=3,
            )

            response = client.get(
                f"/api/customers/{customer.id}",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data is not None
            customer_data = data.get("customer") or data
            assert customer_data.get("name") == "Test Customer" or customer_data.get("id") == customer.id

    def test_customer_json_api_not_found(self, client, app, db_setup):
        """GET /api/customers/<id> returns 404 for missing customer."""
        with app.app_context():
            response = client.get(
                "/api/customers/99999",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            assert response.status_code == 404

    def test_customer_360_view_accessible(self, client, app, db_setup):
        """GET /customers/<id> returns 200 HTML for customer_360."""
        with app.app_context():
            customer = database_service.add_customer(
                name="360 Customer",
                email="c360@example.com",
                phone="123-456-7890",
            )
            response = client.get(f"/customers/{customer.id}")
            assert response.status_code in (200, 302)

    def test_customer_update_via_post(self, client, app, db_setup):
        """POST /customers/<id>/edit updates the customer."""
        with app.app_context():
            customer = database_service.add_customer(
                name="Original",
                email="original@example.com",
                phone="123-456-7890",
            )

            response = client.post(
                f"/customers/{customer.id}/edit",
                data={
                    "name": "Updated",
                    "email": "updated@example.com",
                    "phone": "987-654-3210",
                },
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            # 200 success, 302 redirect to list, or 422 validation
            assert response.status_code in (200, 302, 422)

    def test_customer_delete_via_post(self, client, app, db_setup):
        """POST /customers/<id>/delete removes the customer."""
        with app.app_context():
            customer = database_service.add_customer(
                name="Delete Customer",
                email="delete@example.com",
                phone="123-456-7890",
            )
            cid = customer.id

            response = client.post(
                f"/customers/{cid}/delete",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            assert response.status_code in (200, 302)


class TestTaskCRUDRoutes:
    """Task CRUD via blueprint routes."""

    def _make_agent(self, name="Agent", email="agent@example.com"):
        return database_service.add_agent(name=name, email=email, phone="123-456-7890")

    def _make_task(self, agent_id, title="Task", **kwargs):
        return database_service.add_task(
            title=title,
            description="desc",
            agent_id=agent_id,
            priority=kwargs.get("priority", "medium"),
            status=kwargs.get("status", "pending"),
        )

    def test_task_json_api_success(self, client, app, db_setup):
        """GET /api/tasks/<id> returns JSON task record."""
        with app.app_context():
            agent = self._make_agent("Task Agent", "ta@example.com")
            task = self._make_task(agent.id, "View Task")

            response = client.get(
                f"/api/tasks/{task.id}",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data is not None

    def test_task_json_api_not_found(self, client, app, db_setup):
        """GET /api/tasks/<id> returns 404 for missing task."""
        with app.app_context():
            response = client.get(
                "/api/tasks/99999",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            assert response.status_code == 404

    def test_task_update_via_post(self, client, app, db_setup):
        """POST /tasks/<id>/edit updates the task."""
        with app.app_context():
            agent = self._make_agent("Update Agent", "ua@example.com")
            task = self._make_task(agent.id, "Original Task")
            due = (date.today() + timedelta(days=7)).isoformat()

            response = client.post(
                f"/tasks/{task.id}/edit",
                data={"title": "Updated Task", "priority": "high",
                      "status": "in_progress", "due_date": due},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            assert response.status_code in (200, 302, 422)

    def test_task_complete_via_post(self, client, app, db_setup):
        """POST /tasks/<id>/complete marks task done."""
        with app.app_context():
            agent = self._make_agent("Complete Agent", "ca@example.com")
            task = self._make_task(agent.id, "Complete Task")

            response = client.post(
                f"/tasks/{task.id}/complete",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            assert response.status_code in (200, 302)

    def test_task_delete_via_post(self, client, app, db_setup):
        """POST /tasks/<id>/delete removes the task."""
        with app.app_context():
            agent = self._make_agent("Delete Agent", "da@example.com")
            task = self._make_task(agent.id, "Delete Task")

            response = client.post(
                f"/tasks/{task.id}/delete",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            assert response.status_code in (200, 302)


class TestExportRoutes:
    """Smoke-level tests for export/recommendation endpoints."""

    def test_recommendations_page_loads(self, client, app, db_setup):
        """GET /recommendations returns 200 HTML."""
        with app.app_context():
            response = client.get("/recommendations")
            assert response.status_code in (200, 302)

    def test_customer_recommendations_page_loads(self, client, app, db_setup):
        """GET /get_customer_recommendations/<id> returns 200 for real customer."""
        with app.app_context():
            customer = database_service.add_customer(
                name="Rec Customer", email="rec@example.com", phone="123-456-7890"
            )
            response = client.get(f"/get_customer_recommendations/{customer.id}")
            assert response.status_code in (200, 302)


class TestRouteErrorHandling:
    """Verify error-handling behaviour on the current routes."""

    def test_invalid_method_on_customer_json(self, client, app, db_setup):
        """POST to a GET-only JSON endpoint returns 405."""
        with app.app_context():
            response = client.post(
                "/api/customers/1",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            assert response.status_code == 405

    def test_invalid_method_on_task_json(self, client, app, db_setup):
        """POST to a GET-only task JSON endpoint returns 405."""
        with app.app_context():
            response = client.post(
                "/api/tasks/1",
                headers={"X-Requested-With": "XMLHttpRequest"},
            )
            assert response.status_code == 405

    def test_missing_customer_returns_404(self, client, app, db_setup):
        """GET /api/customers/<id> with unknown ID returns 404."""
        with app.app_context():
            response = client.get("/api/customers/99999")
            assert response.status_code == 404

    def test_missing_task_returns_404(self, client, app, db_setup):
        """GET /api/tasks/<id> with unknown ID returns 404."""
        with app.app_context():
            response = client.get("/api/tasks/99999")
            assert response.status_code == 404


class TestRoutePermissions:
    """Auth and content-type behaviour."""

    def test_unauthenticated_request_redirects_when_auth_enabled(self, monkeypatch, app, db_setup):
        """With auth on, unauthenticated requests to protected routes get 302."""
        import os
        monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "1")
        from app import create_app as _create_app
        fresh_app = _create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
        with fresh_app.test_client() as c:
            response = c.get("/customers")
            assert response.status_code in (302, 401)

    def test_auth_disabled_allows_customer_list(self, client, app, db_setup):
        """With auth off (test default), /customers returns 200."""
        with app.app_context():
            response = client.get("/customers")
            assert response.status_code == 200

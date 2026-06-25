"""
Comprehensive tests for all CRUD routes with various scenarios
"""

import pytest
from datetime import date, timedelta
from services.database_service import database_service


class TestCustomerCRUDRoutes:
    """Test customer CRUD route functionality"""

    def test_customer_view_route_success(self, client, app, db_setup):
        """Test GET /customers/<id> route"""
        with app.app_context():
            # Create test customer
            customer = database_service.add_customer(
                name="Test Customer",
                email="test@example.com",
                phone="123-456-7890",
                budget_min=100000,
                budget_max=200000,
                preferred_bedrooms=3,
                preferred_bathrooms=2,
                preferred_type="house",
                location_preference="downtown"
            )
            
            response = client.get(f'/customers/{customer.id}',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['customer']['name'] == "Test Customer"
            assert data['customer']['budget_min'] == 100000
            assert data['customer']['preferred_bedrooms'] == 3

    def test_customer_view_route_not_found(self, client, app, db_setup):
        """Test GET /customers/<id> route with non-existent customer"""
        with app.app_context():
            response = client.get('/customers/99999',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 404
            data = response.get_json()
            assert data['error'] == 'Customer not found'

    def test_customer_edit_route_get(self, client, app, db_setup):
        """Test GET /customers/<id>/edit route"""
        with app.app_context():
            customer = database_service.add_customer(
                name="Edit Customer",
                email="edit@example.com",
                phone="123-456-7890",
                budget_min=150000,
                budget_max=250000
            )
            
            response = client.get(f'/customers/{customer.id}/edit',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['customer']['name'] == "Edit Customer"
            assert data['customer']['budget_min'] == 150000

    def test_customer_update_route_success(self, client, app, db_setup):
        """Test PUT /customers/<id> route with valid data"""
        with app.app_context():
            customer = database_service.add_customer(
                name="Original Customer",
                email="original@example.com",
                phone="123-456-7890"
            )
            
            response = client.post(f'/customers/{customer.id}',
                                 data={
                                     'name': 'Updated Customer',
                                     'email': 'updated@example.com',
                                     'phone': '987-654-3210',
                                     'budget_min': 200000,
                                     'budget_max': 300000,
                                     'preferred_bedrooms': 4,
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            
            # Verify update
            updated_customer = database_service.get_customer(customer.id)
            assert updated_customer.name == 'Updated Customer'
            assert updated_customer.budget_min == 200000

    def test_customer_update_budget_validation(self, client, app, db_setup):
        """Test customer update with invalid budget range"""
        with app.app_context():
            customer = database_service.add_customer(
                name="Test Customer",
                email="test@example.com",
                phone="123-456-7890"
            )
            
            response = client.post(f'/customers/{customer.id}',
                                 data={
                                     'name': 'Test Customer',
                                     'email': 'test@example.com',
                                     'phone': '123-456-7890',
                                     'budget_min': 300000,
                                     'budget_max': 200000,  # Max less than min
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['error'] == 'Validation failed'
            assert 'budget_max' in data['errors']

    def test_customer_delete_route_success(self, client, app, db_setup):
        """Test DELETE /customers/<id> route"""
        with app.app_context():
            customer = database_service.add_customer(
                name="Delete Customer",
                email="delete@example.com",
                phone="123-456-7890"
            )
            
            response = client.delete(f'/customers/{customer.id}',
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            
            # Verify deletion
            deleted_customer = database_service.get_customer(customer.id)
            assert deleted_customer is None


class TestTaskCRUDRoutes:
    """Test task CRUD route functionality"""

    def test_task_view_route_success(self, client, app, db_setup):
        """Test GET /tasks/<id> route"""
        with app.app_context():
            agent = database_service.add_agent(
                name="Task Agent",
                email="taskagent@example.com",
                phone="123-456-7890"
            )
            
            due_date = date.today() + timedelta(days=7)
            task = database_service.add_task(
                title="View Task",
                description="Task for viewing test",
                agent_id=agent.id,
                priority="high",
                status="pending",
                due_date=due_date
            )
            
            response = client.get(f'/tasks/{task.id}',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['task']['title'] == "View Task"
            assert data['task']['priority'] == "high"
            assert data['agent']['name'] == "Task Agent"

    def test_task_edit_route_get(self, client, app, db_setup):
        """Test GET /tasks/<id>/edit route"""
        with app.app_context():
            agent = database_service.add_agent(
                name="Edit Agent",
                email="editagent@example.com",
                phone="123-456-7890"
            )
            
            task = database_service.add_task(
                title="Edit Task",
                description="Task for editing test",
                agent_id=agent.id,
                priority="medium",
                status="in_progress"
            )
            
            response = client.get(f'/tasks/{task.id}/edit',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['task']['title'] == "Edit Task"
            assert data['task']['status'] == "in_progress"

    def test_task_update_route_success(self, client, app, db_setup):
        """Test PUT /tasks/<id> route with valid data"""
        with app.app_context():
            agent = database_service.add_agent(
                name="Update Agent",
                email="updateagent@example.com",
                phone="123-456-7890"
            )
            
            task = database_service.add_task(
                title="Original Task",
                description="Original description",
                agent_id=agent.id,
                priority="low",
                status="pending"
            )
            
            new_due_date = date.today() + timedelta(days=14)
            response = client.post(f'/tasks/{task.id}',
                                 data={
                                     'title': 'Updated Task',
                                     'description': 'Updated description',
                                     'priority': 'high',
                                     'status': 'completed',
                                     'due_date': new_due_date.isoformat(),
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            
            # Verify update
            updated_task = database_service.get_task(task.id)
            assert updated_task.title == 'Updated Task'
            assert updated_task.priority == 'high'
            assert updated_task.status == 'completed'

    def test_task_update_due_date_validation(self, client, app, db_setup):
        """Test task update with past due date"""
        with app.app_context():
            agent = database_service.add_agent(
                name="Validation Agent",
                email="validation@example.com",
                phone="123-456-7890"
            )
            
            task = database_service.add_task(
                title="Validation Task",
                description="Task for validation test",
                agent_id=agent.id
            )
            
            past_date = date.today() - timedelta(days=1)
            response = client.post(f'/tasks/{task.id}',
                                 data={
                                     'title': 'Validation Task',
                                     'description': 'Task for validation test',
                                     'priority': 'medium',
                                     'status': 'pending',
                                     'due_date': past_date.isoformat(),
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['error'] == 'Validation failed'
            assert 'due_date' in data['errors']

    def test_task_delete_route_success(self, client, app, db_setup):
        """Test DELETE /tasks/<id> route"""
        with app.app_context():
            agent = database_service.add_agent(
                name="Delete Agent",
                email="deleteagent@example.com",
                phone="123-456-7890"
            )
            
            task = database_service.add_task(
                title="Delete Task",
                description="Task for deletion test",
                agent_id=agent.id
            )
            
            response = client.delete(f'/tasks/{task.id}',
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            
            # Verify deletion
            deleted_task = database_service.get_task(task.id)
            assert deleted_task is None


class TestExportRoutes:
    """Test export functionality routes"""

    def test_recommendations_export_all_properties(self, client, app, db_setup):
        """Test GET /recommendations/export without customer filter"""
        with app.app_context():
            # Create test data
            agent = database_service.add_agent(
                name="Export Agent",
                email="export@example.com",
                phone="123-456-7890"
            )
            
            database_service.add_property(
                title="Export Property 1",
                address="123 Export St",
                price=200000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1500,
                description="First export property",
                status="active",
                agent_id=agent.id
            )
            
            database_service.add_property(
                title="Export Property 2",
                address="456 Export Ave",
                price=250000,
                property_type="condo",
                bedrooms=2,
                bathrooms=2,
                square_feet=1200,
                description="Second export property",
                status="active",
                agent_id=agent.id
            )
            
            response = client.get('/recommendations/export',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['customer_id'] is None
            assert data['total_properties'] == 2
            assert len(data['properties']) == 2

    def test_recommendations_export_filtered_by_customer(self, client, app, db_setup):
        """Test GET /recommendations/export with customer filter"""
        with app.app_context():
            # Create customer with preferences
            customer = database_service.add_customer(
                name="Filter Customer",
                email="filter@example.com",
                phone="123-456-7890",
                budget_min=150000,
                budget_max=250000,
                preferred_bedrooms=3,
                preferred_type="house"
            )
            
            agent = database_service.add_agent(
                name="Filter Agent",
                email="filteragent@example.com",
                phone="987-654-3210"
            )
            
            # Create matching property
            database_service.add_property(
                title="Matching Property",
                address="123 Match St",
                price=200000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1500,
                description="Matches customer preferences",
                status="active",
                agent_id=agent.id
            )
            
            # Create non-matching property (too expensive)
            database_service.add_property(
                title="Expensive Property",
                address="456 Expensive Ave",
                price=300000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1800,
                description="Too expensive for customer",
                status="active",
                agent_id=agent.id
            )
            
            response = client.get(f'/recommendations/export?customer_id={customer.id}',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['customer_id'] == customer.id
            assert data['total_properties'] == 1
            assert data['properties'][0]['title'] == "Matching Property"

    def test_property_viewing_schedule_route(self, client, app, db_setup):
        """Test GET /properties/<id>/schedule-viewing route"""
        with app.app_context():
            property_obj = database_service.add_property(
                title="Viewing Property",
                address="789 Viewing St",
                price=180000,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1400,
                description="Property for viewing"
            )
            
            response = client.get(f'/properties/{property_obj.id}/schedule-viewing',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['property']['title'] == "Viewing Property"
            assert data['property']['address'] == "789 Viewing St"

    def test_property_viewing_schedule_not_found(self, client, app, db_setup):
        """Test property viewing schedule with non-existent property"""
        with app.app_context():
            response = client.get('/properties/99999/schedule-viewing',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 404
            data = response.get_json()
            assert data['error'] == 'Property not found'


class TestRouteErrorHandling:
    """Test error handling across all CRUD routes"""

    def test_invalid_method_handling(self, client, app, db_setup):
        """Test handling of invalid HTTP methods"""
        with app.app_context():
            agent = database_service.add_agent(
                name="Method Agent",
                email="method@example.com",
                phone="123-456-7890"
            )
            
            # Test invalid method on agent route
            response = client.patch(f'/agents/{agent.id}',
                                  headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 405  # Method Not Allowed

    def test_malformed_json_handling(self, client, app, db_setup):
        """Test handling of malformed JSON requests"""
        with app.app_context():
            agent = database_service.add_agent(
                name="JSON Agent",
                email="json@example.com",
                phone="123-456-7890"
            )
            
            # Send malformed JSON
            response = client.post(f'/agents/{agent.id}',
                                 data='{"invalid": json}',
                                 content_type='application/json',
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            # Should handle gracefully and return validation error
            assert response.status_code in [400, 422]

    def test_missing_csrf_token_handling(self, client, app, db_setup):
        """Test CSRF token handling in forms"""
        with app.app_context():
            agent = database_service.add_agent(
                name="CSRF Agent",
                email="csrf@example.com",
                phone="123-456-7890"
            )
            
            # Test without CSRF token (should still work for AJAX requests)
            response = client.post(f'/agents/{agent.id}',
                                 data={
                                     'name': 'Updated CSRF Agent',
                                     'email': 'updated-csrf@example.com',
                                     'phone': '987-654-3210',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            # Should work since we're using BaseNoCSRFForm for AJAX
            assert response.status_code == 200

    def test_database_constraint_violations(self, client, app, db_setup):
        """Test handling of database constraint violations"""
        with app.app_context():
            # Create agent with unique email
            agent1 = database_service.add_agent(
                name="Unique Agent 1",
                email="unique@example.com",
                phone="123-456-7890"
            )
            
            agent2 = database_service.add_agent(
                name="Unique Agent 2",
                email="unique2@example.com",
                phone="987-654-3210"
            )
            
            # Try to update agent2 with agent1's email
            response = client.post(f'/agents/{agent2.id}',
                                 data={
                                     'name': 'Unique Agent 2',
                                     'email': 'unique@example.com',  # Duplicate
                                     'phone': '987-654-3210',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['error'] == 'Validation failed'

    def test_large_payload_handling(self, client, app, db_setup):
        """Test handling of large payloads"""
        with app.app_context():
            agent = database_service.add_agent(
                name="Large Agent",
                email="large@example.com",
                phone="123-456-7890"
            )
            
            # Send very large bio field
            large_bio = "x" * 10000  # 10KB of text
            
            response = client.post(f'/agents/{agent.id}',
                                 data={
                                     'name': 'Large Agent',
                                     'email': 'large@example.com',
                                     'phone': '123-456-7890',
                                     'bio': large_bio,
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            # Should handle gracefully (either accept or reject with proper error)
            assert response.status_code in [200, 400, 413]

    def test_concurrent_delete_handling(self, client, app, db_setup):
        """Test handling of concurrent delete operations"""
        with app.app_context():
            agent = database_service.add_agent(
                name="Concurrent Agent",
                email="concurrent@example.com",
                phone="123-456-7890"
            )
            
            # First delete should succeed
            response1 = client.delete(f'/agents/{agent.id}',
                                    headers={'X-Requested-With': 'XMLHttpRequest'})
            assert response1.status_code == 200
            
            # Second delete should return 404
            response2 = client.delete(f'/agents/{agent.id}',
                                    headers={'X-Requested-With': 'XMLHttpRequest'})
            assert response2.status_code == 404


class TestRoutePermissions:
    """Test route permissions and access control"""

    def test_html_fallback_responses(self, client, app, db_setup):
        """Test HTML fallback for non-AJAX requests"""
        with app.app_context():
            agent = database_service.add_agent(
                name="HTML Agent",
                email="html@example.com",
                phone="123-456-7890"
            )
            
            # Test HTML request (no AJAX header)
            response = client.post(f'/agents/{agent.id}',
                                 data={
                                     'name': 'Updated HTML Agent',
                                     'email': 'updated-html@example.com',
                                     'phone': '987-654-3210',
                                     '_method': 'PUT'
                                 },
                                 follow_redirects=True)
            
            # Should redirect or return HTML response
            assert response.status_code == 200
            assert b'html' in response.data.lower() or response.status_code == 302

    def test_content_type_negotiation(self, client, app, db_setup):
        """Test content type negotiation"""
        with app.app_context():
            agent = database_service.add_agent(
                name="Content Agent",
                email="content@example.com",
                phone="123-456-7890"
            )
            
            # Test with Accept: application/json
            response = client.get(f'/agents/{agent.id}/edit',
                                headers={'Accept': 'application/json'})
            
            if response.status_code == 200:
                assert response.content_type.startswith('application/json')
            
            # Test with Accept: text/html
            response = client.get(f'/agents/{agent.id}/edit',
                                headers={'Accept': 'text/html'})
            
            # Should return HTML or redirect
            assert response.status_code in [200, 302, 404]

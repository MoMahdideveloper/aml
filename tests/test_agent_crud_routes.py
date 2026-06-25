"""
Integration tests for agent CRUD routes
"""

import pytest
from flask import url_for
from services.database_service import database_service
from services.monitoring_service import monitoring_service


class TestAgentCRUDRoutes:
    """Test agent CRUD route functionality"""

    def test_agent_edit_route_get(self, client, app, db_setup):
        """Test GET /agents/<id>/edit route"""
        with app.app_context():
            # Create test agent
            agent = database_service.add_agent(
                name="Test Agent",
                email="test@example.com",
                phone="123-456-7890",
                specialization="Residential",
                bio="Test bio"
            )
            
            # Test GET request for edit form
            response = client.get(f'/agents/{agent.id}/edit', 
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data is not None, f"Expected JSON response, got: {response.data}"
            assert 'agent' in data
            assert data['agent']['name'] == "Test Agent"
            assert data['agent']['email'] == "test@example.com"

    def test_agent_edit_route_get_not_found(self, client, app, db_setup):
        """Test GET /agents/<id>/edit route with non-existent agent"""
        with app.app_context():
            response = client.get('/agents/99999/edit',
                                headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 404
            data = response.get_json()
            assert 'error' in data
            assert data['error'] == 'Agent not found'

    def test_agent_update_route_success(self, client, app, db_setup):
        """Test PUT /agents/<id> route with valid data"""
        with app.app_context():
            # Create test agent
            agent = database_service.add_agent(
                name="Test Agent",
                email="test@example.com",
                phone="123-456-7890"
            )
            
            # Test update
            response = client.post(f'/agents/{agent.id}',
                                 data={
                                     'name': 'Updated Agent',
                                     'email': 'updated@example.com',
                                     'phone': '987-654-3210',
                                     'specialization': 'Commercial',
                                     'bio': 'Updated bio',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'Agent "Updated Agent" updated successfully!' in data['message']
            
            # Verify agent was updated
            updated_agent = database_service.get_agent(agent.id)
            assert updated_agent.name == 'Updated Agent'
            assert updated_agent.email == 'updated@example.com'

    def test_agent_update_route_validation_error(self, client, app, db_setup):
        """Test PUT /agents/<id> route with invalid data"""
        with app.app_context():
            # Create test agent
            agent = database_service.add_agent(
                name="Test Agent",
                email="test@example.com",
                phone="123-456-7890"
            )
            
            # Test update with invalid email
            response = client.post(f'/agents/{agent.id}',
                                 data={
                                     'name': 'Updated Agent',
                                     'email': 'invalid-email',  # Invalid email
                                     'phone': '987-654-3210',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['error'] == 'Validation failed'
            assert 'errors' in data

    def test_agent_update_route_not_found(self, client, app, db_setup):
        """Test PUT /agents/<id> route with non-existent agent"""
        with app.app_context():
            response = client.post('/agents/99999',
                                 data={
                                     'name': 'Updated Agent',
                                     'email': 'updated@example.com',
                                     'phone': '987-654-3210',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 404
            data = response.get_json()
            assert data['error'] == 'Agent not found'

    def test_agent_delete_route_success(self, client, app, db_setup):
        """Test DELETE /agents/<id> route"""
        with app.app_context():
            # Create test agent
            agent = database_service.add_agent(
                name="Test Agent",
                email="test@example.com",
                phone="123-456-7890"
            )
            
            # Test delete
            response = client.delete(f'/agents/{agent.id}',
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            assert 'Agent "Test Agent" deleted successfully!' in data['message']
            
            # Verify agent was deleted
            deleted_agent = database_service.get_agent(agent.id)
            assert deleted_agent is None

    def test_agent_delete_route_not_found(self, client, app, db_setup):
        """Test DELETE /agents/<id> route with non-existent agent"""
        with app.app_context():
            response = client.delete('/agents/99999',
                                   headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 404
            data = response.get_json()
            assert data['error'] == 'Agent not found'

    def test_agent_routes_html_fallback(self, client, app, db_setup):
        """Test that routes work with HTML requests (non-AJAX)"""
        with app.app_context():
            # Create test agent
            agent = database_service.add_agent(
                name="Test Agent",
                email="test@example.com",
                phone="123-456-7890"
            )
            
            # Test HTML update request
            response = client.post(f'/agents/{agent.id}',
                                 data={
                                     'name': 'Updated Agent',
                                     'email': 'updated@example.com',
                                     'phone': '987-654-3210',
                                     '_method': 'PUT'
                                 },
                                 follow_redirects=True)
            
            assert response.status_code == 200
            
            # Test HTML delete request
            response = client.delete(f'/agents/{agent.id}',
                                   follow_redirects=True)
            
            assert response.status_code == 200

    def test_agent_edit_email_uniqueness_validation(self, client, app, db_setup):
        """Test email uniqueness validation in agent edit"""
        with app.app_context():
            # Create two test agents
            agent1 = database_service.add_agent(
                name="Agent 1",
                email="agent1@example.com",
                phone="123-456-7890"
            )
            
            agent2 = database_service.add_agent(
                name="Agent 2", 
                email="agent2@example.com",
                phone="987-654-3210"
            )
            
            # Try to update agent2 with agent1's email
            response = client.post(f'/agents/{agent2.id}',
                                 data={
                                     'name': 'Agent 2',
                                     'email': 'agent1@example.com',  # Duplicate email
                                     'phone': '987-654-3210',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 400
            data = response.get_json()
            assert data['error'] == 'Validation failed'
            assert 'email' in data['errors']

    def test_agent_edit_same_email_allowed(self, client, app, db_setup):
        """Test that agent can keep their own email when editing"""
        with app.app_context():
            # Create test agent
            agent = database_service.add_agent(
                name="Test Agent",
                email="test@example.com",
                phone="123-456-7890"
            )
            
            # Update agent with same email (should be allowed)
            response = client.post(f'/agents/{agent.id}',
                                 data={
                                     'name': 'Updated Agent',
                                     'email': 'test@example.com',  # Same email
                                     'phone': '987-654-3210',
                                     '_method': 'PUT'
                                 },
                                 headers={'X-Requested-With': 'XMLHttpRequest'})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

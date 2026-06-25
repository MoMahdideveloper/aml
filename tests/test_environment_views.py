"""
Tests for environment controller endpoints.
Tests web interface, authentication, CRUD operations, and error handling.
"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock
from flask import url_for

from services.environment_service import environment_service
from sqlalchemy_models import EnvironmentVariable


class TestEnvironmentViews:
    """Test cases for environment management views"""

    @pytest.fixture
    def authenticated_client(self, client, app):
        """Create authenticated client for admin operations"""
        with app.app_context():
            # Set admin password
            os.environ['ADMIN_PASSWORD'] = 'test_admin_password'
            
            # Login via session
            with client.session_transaction() as sess:
                sess['admin_authenticated'] = True
                sess['admin_user'] = 'admin'
        
        return client

    def test_environment_page_unauthenticated(self, client):
        """Test accessing environment page without authentication"""
        response = client.get('/admin/environment')
        assert response.status_code == 401
        assert b'Admin authentication required' in response.data

    def test_environment_page_authenticated(self, authenticated_client, db_setup):
        """Test accessing environment page with authentication"""
        response = authenticated_client.get('/admin/environment')
        assert response.status_code == 200
        assert b'Environment Variables' in response.data or b'admin_environment' in response.data

    def test_admin_login_page(self, client):
        """Test admin login page"""
        response = client.get('/admin/login')
        assert response.status_code == 200
        assert b'password' in response.data.lower()

    def test_admin_login_success(self, client):
        """Test successful admin login"""
        os.environ['ADMIN_PASSWORD'] = 'test_password'
        
        response = client.post('/admin/login', data={
            'password': 'test_password'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to environment page after login

    def test_admin_login_failure(self, client):
        """Test failed admin login"""
        os.environ['ADMIN_PASSWORD'] = 'correct_password'
        
        response = client.post('/admin/login', data={
            'password': 'wrong_password'
        })
        
        assert response.status_code == 200
        assert b'Invalid admin password' in response.data

    def test_admin_logout(self, authenticated_client):
        """Test admin logout"""
        response = authenticated_client.get('/admin/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'Logged out successfully' in response.data

    def test_create_environment_variable_success(self, authenticated_client, db_setup):
        """Test successful environment variable creation via form"""
        response = authenticated_client.post('/admin/environment', data={
            'key': 'TEST_CREATE_VAR',
            'value': 'test_value',
            'description': 'Test variable',
            'is_required': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'created successfully' in response.data
        
        # Verify variable was created
        variable = EnvironmentVariable.query.filter_by(key='TEST_CREATE_VAR').first()
        assert variable is not None
        assert variable.value == 'test_value'

    def test_create_environment_variable_duplicate(self, authenticated_client, db_setup):
        """Test creating duplicate environment variable"""
        # Create first variable
        environment_service.create_variable(key='DUPLICATE_VAR', value='value1')
        
        # Try to create duplicate
        response = authenticated_client.post('/admin/environment', data={
            'key': 'DUPLICATE_VAR',
            'value': 'value2',
            'description': 'Duplicate test'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'already exists' in response.data

    def test_create_environment_variable_invalid_key(self, authenticated_client, db_setup):
        """Test creating variable with invalid key"""
        response = authenticated_client.post('/admin/environment', data={
            'key': '123_INVALID_KEY',
            'value': 'test_value'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid Key Format' in response.data or b'validation failed' in response.data

    def test_create_environment_variable_form_validation(self, authenticated_client, db_setup):
        """Test form validation for environment variable creation"""
        # Test missing required fields
        response = authenticated_client.post('/admin/environment', data={
            'key': '',  # Empty key
            'value': 'test_value'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'validation failed' in response.data or b'required' in response.data

    def test_update_environment_variable_success(self, authenticated_client, db_setup):
        """Test successful environment variable update via AJAX"""
        # Create variable first
        environment_service.create_variable(key='UPDATE_TEST', value='original_value')
        
        # Update via AJAX
        response = authenticated_client.put('/admin/environment/UPDATE_TEST',
            data=json.dumps({
                'value': 'updated_value',
                'description': 'Updated description',
                'is_required': True
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'updated successfully' in data['message']
        
        # Verify update in database
        variable = EnvironmentVariable.query.filter_by(key='UPDATE_TEST').first()
        assert variable.description == 'Updated description'

    def test_update_environment_variable_not_found(self, authenticated_client, db_setup):
        """Test updating non-existent environment variable"""
        response = authenticated_client.put('/admin/environment/NON_EXISTENT',
            data=json.dumps({'value': 'new_value'}),
            content_type='application/json'
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error']

    def test_update_environment_variable_invalid_request(self, authenticated_client, db_setup):
        """Test updating with invalid request format"""
        environment_service.create_variable(key='UPDATE_INVALID', value='original')
        
        # Test non-JSON request
        response = authenticated_client.put('/admin/environment/UPDATE_INVALID',
            data='not json',
            content_type='text/plain'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'JSON format' in data['error']

    def test_update_environment_variable_missing_value(self, authenticated_client, db_setup):
        """Test updating without required value field"""
        environment_service.create_variable(key='UPDATE_NO_VALUE', value='original')
        
        response = authenticated_client.put('/admin/environment/UPDATE_NO_VALUE',
            data=json.dumps({'description': 'New description'}),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'required' in data['error']

    def test_delete_environment_variable_success(self, authenticated_client, db_setup):
        """Test successful environment variable deletion"""
        # Create variable first
        environment_service.create_variable(key='DELETE_TEST', value='test_value')
        
        # Delete via AJAX
        response = authenticated_client.delete('/admin/environment/DELETE_TEST')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'deleted successfully' in data['message']
        
        # Verify deletion
        variable = EnvironmentVariable.query.filter_by(key='DELETE_TEST').first()
        assert variable is None

    def test_delete_environment_variable_not_found(self, authenticated_client, db_setup):
        """Test deleting non-existent environment variable"""
        response = authenticated_client.delete('/admin/environment/NON_EXISTENT')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error']

    def test_delete_required_environment_variable(self, authenticated_client, db_setup):
        """Test deleting required environment variable"""
        # Create required variable
        environment_service.create_variable(key='REQUIRED_DELETE', value='test', is_required=True)
        
        response = authenticated_client.delete('/admin/environment/REQUIRED_DELETE')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'required' in data['error']

    def test_delete_critical_system_variable(self, authenticated_client, db_setup):
        """Test deleting critical system variable"""
        # Create critical variable directly in database to bypass validation
        from sqlalchemy_models import EnvironmentVariable
        variable = EnvironmentVariable(
            key='FLASK_SECRET_KEY',
            value='secret',
            is_sensitive=True
        )
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        response = authenticated_client.delete('/admin/environment/FLASK_SECRET_KEY')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'critical' in data['error']

    def test_get_environment_variable_details(self, authenticated_client, db_setup):
        """Test getting environment variable details for editing"""
        # Create variable
        environment_service.create_variable(
            key='DETAILS_TEST',
            value='test_value',
            description='Test description'
        )
        
        response = authenticated_client.get('/admin/environment/DETAILS_TEST/details')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['variable']['key'] == 'DETAILS_TEST'
        assert data['variable']['description'] == 'Test description'

    def test_get_environment_variable_details_not_found(self, authenticated_client, db_setup):
        """Test getting details for non-existent variable"""
        response = authenticated_client.get('/admin/environment/NON_EXISTENT/details')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error']

    def test_get_validation_summary(self, authenticated_client, db_setup):
        """Test getting validation summary"""
        # Create test variables
        environment_service.create_variable(key='VALID_VAR', value='valid')
        environment_service.create_variable(key='REQUIRED_VAR', value='required', is_required=True)
        
        response = authenticated_client.get('/admin/environment/validation')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'validation' in data
        assert 'total_variables' in data['validation']

    def test_environment_history_page(self, authenticated_client, db_setup):
        """Test environment change history page"""
        # Create and modify variable to generate history
        environment_service.create_variable(key='HISTORY_VAR', value='original')
        environment_service.update_variable(key='HISTORY_VAR', value='updated')
        
        response = authenticated_client.get('/admin/environment/history')
        
        assert response.status_code == 200
        assert b'history' in response.data.lower()

    def test_environment_history_with_filter(self, authenticated_client, db_setup):
        """Test environment history with variable filter"""
        # Create and modify variable
        environment_service.create_variable(key='FILTER_VAR', value='original')
        environment_service.update_variable(key='FILTER_VAR', value='updated')
        
        response = authenticated_client.get('/admin/environment/history?variable_key=FILTER_VAR')
        
        assert response.status_code == 200

    def test_authentication_via_basic_auth(self, client):
        """Test authentication via Basic Auth header"""
        import base64
        
        os.environ['ADMIN_PASSWORD'] = 'basic_auth_password'
        
        # Create Basic Auth header
        credentials = base64.b64encode(b'admin:basic_auth_password').decode('utf-8')
        headers = {'Authorization': f'Basic {credentials}'}
        
        response = client.get('/admin/environment', headers=headers)
        assert response.status_code == 200

    def test_authentication_via_form_post(self, client):
        """Test authentication via form POST"""
        os.environ['ADMIN_PASSWORD'] = 'form_password'
        
        response = client.post('/admin/environment', data={
            'admin_password': 'form_password',
            'key': 'TEST_VAR',
            'value': 'test_value'
        }, follow_redirects=True)
        
        # Should be authenticated and process the form
        assert response.status_code == 200

    def test_unauthenticated_ajax_requests(self, client):
        """Test that AJAX requests return JSON error when unauthenticated"""
        response = client.put('/admin/environment/TEST_VAR',
            data=json.dumps({'value': 'new_value'}),
            content_type='application/json'
        )
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'Admin authentication required'

    @patch('views.admin_environment.environment_service')
    def test_environment_page_service_error(self, mock_service, authenticated_client):
        """Test environment page when service throws error"""
        mock_service.get_all_variables.side_effect = Exception("Service error")
        mock_service.get_validation_summary.side_effect = Exception("Validation error")
        
        response = authenticated_client.get('/admin/environment')
        
        assert response.status_code == 200
        assert b'Critical Error' in response.data or b'Unable to load' in response.data

    @patch('views.admin_environment.environment_service')
    def test_create_variable_service_error(self, mock_service, authenticated_client):
        """Test creating variable when service throws error"""
        mock_service.create_variable.side_effect = RuntimeError("Runtime error")
        
        response = authenticated_client.post('/admin/environment', data={
            'key': 'ERROR_TEST',
            'value': 'test_value'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Runtime Error' in response.data

    @patch('views.admin_environment.environment_service')
    def test_update_variable_service_error(self, mock_service, authenticated_client):
        """Test updating variable when service throws error"""
        mock_service.update_variable.side_effect = RuntimeError("Update error")
        
        response = authenticated_client.put('/admin/environment/ERROR_VAR',
            data=json.dumps({'value': 'new_value'}),
            content_type='application/json'
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'runtime_error' in data['error_type']

    @patch('views.admin_environment.environment_service')
    def test_delete_variable_service_error(self, mock_service, authenticated_client):
        """Test deleting variable when service throws error"""
        mock_service.delete_variable.side_effect = RuntimeError("Delete error")
        
        response = authenticated_client.delete('/admin/environment/ERROR_VAR')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'runtime_error' in data['error_type']

    def test_security_warnings_display(self, authenticated_client, db_setup):
        """Test that security warnings are displayed to user"""
        # Create variable that will trigger security warnings
        response = authenticated_client.post('/admin/environment', data={
            'key': 'PUBLIC_VAR',
            'value': 'password123',  # Should trigger warning
            'description': 'Test with security issue'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should show security warning
        assert b'Security Warning' in response.data or b'warning' in response.data

    def test_validation_summary_warnings(self, authenticated_client, db_setup):
        """Test that validation summary shows warnings on page"""
        # Create variables with issues
        environment_service.create_variable(key='MISSING_REQ', value='test', is_required=True)
        
        # Remove from runtime to trigger missing required warning
        os.environ.pop('MISSING_REQ', None)
        
        response = authenticated_client.get('/admin/environment')
        
        assert response.status_code == 200
        # Should show warnings about missing required variables
        assert b'Warning' in response.data or b'required variables' in response.data

    def test_rollback_environment_changes(self, authenticated_client, db_setup):
        """Test environment rollback functionality"""
        with patch('services.environment_service.runtime_environment_manager') as mock_manager:
            mock_manager.rollback_changes.return_value = {
                'success': True,
                'message': 'Rollback successful',
                'variables_restored': 2,
                'variables_failed': 0,
                'errors': []
            }
            
            response = authenticated_client.post('/admin/environment/rollback')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'Rollback successful' in data['message']

    def test_rollback_no_backup_available(self, authenticated_client, db_setup):
        """Test rollback when no backup is available"""
        with patch('services.environment_service.runtime_environment_manager') as mock_manager:
            mock_manager.rollback_changes.side_effect = ValueError("No backup available")
            
            response = authenticated_client.post('/admin/environment/rollback')
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert data['error_type'] == 'no_backup'

    def test_environment_health_check(self, authenticated_client, db_setup):
        """Test environment health check endpoint"""
        with patch('services.environment_service.runtime_environment_manager') as mock_manager:
            mock_manager._validate_application_health.return_value = {
                'success': True,
                'warnings': [],
                'error': None
            }
            
            response = authenticated_client.get('/admin/environment/health-check')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'health_status' in data

    def test_health_check_failure(self, authenticated_client, db_setup):
        """Test health check when validation fails"""
        with patch('services.environment_service.runtime_environment_manager') as mock_manager:
            mock_manager._validate_application_health.side_effect = Exception("Health check failed")
            
            response = authenticated_client.get('/admin/environment/health-check')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'health_check_error' in data['error_type']

    def test_csrf_protection_considerations(self, authenticated_client, db_setup):
        """Test CSRF considerations for state-changing operations"""
        # Note: This test assumes CSRF protection might be added later
        # For now, we test that the endpoints work with proper authentication
        
        # Test that authenticated requests work
        response = authenticated_client.post('/admin/environment', data={
            'key': 'CSRF_TEST',
            'value': 'test_value'
        })
        
        # Should work with proper authentication
        assert response.status_code in [200, 302]  # Success or redirect

    def test_concurrent_access_handling(self, authenticated_client, db_setup):
        """Test handling of concurrent access to environment variables"""
        # Create variable
        environment_service.create_variable(key='CONCURRENT_TEST', value='original')
        
        # Simulate concurrent updates (this is a basic test)
        response1 = authenticated_client.put('/admin/environment/CONCURRENT_TEST',
            data=json.dumps({'value': 'update1'}),
            content_type='application/json'
        )
        
        response2 = authenticated_client.put('/admin/environment/CONCURRENT_TEST',
            data=json.dumps({'value': 'update2'}),
            content_type='application/json'
        )
        
        # Both should succeed (last one wins)
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify final state
        variable = EnvironmentVariable.query.filter_by(key='CONCURRENT_TEST').first()
        assert variable.value == 'update2'

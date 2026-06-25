"""
Tests for deal CRUD routes
"""

import json
import pytest
from flask import url_for
from services.database_service import database_service


class TestDealCRUDRoutes:
    """Test deal CRUD operations routes"""

    def test_deal_view_route_success(self, client, sample_data):
        """Test successful deal view"""
        # Get a deal ID from sample data
        deals = database_service.get_deals()
        assert len(deals) > 0
        deal_id = deals[0].id
        
        # Test JSON response
        response = client.get(f'/deals/{deal_id}', headers={'Accept': 'application/json'})
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'id' in data
        assert 'status' in data
        assert 'property' in data
        assert 'customer' in data
        assert 'agent' in data

    def test_deal_view_route_not_found(self, client):
        """Test deal view with non-existent ID"""
        response = client.get('/deals/99999', headers={'Accept': 'application/json'})
        assert response.status_code == 404
        
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Deal not found'

    def test_deal_delete_route_success(self, client, sample_data):
        """Test successful deal deletion"""
        # Get a deal ID from sample data
        deals = database_service.get_deals()
        assert len(deals) > 0
        deal_id = deals[0].id
        
        # Delete the deal
        response = client.delete(f'/deals/{deal_id}', headers={'Accept': 'application/json'})
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'message' in data
        assert 'deleted successfully' in data['message']
        
        # Verify deal is deleted
        deleted_deal = database_service.get_deal(deal_id)
        assert deleted_deal is None

    def test_deal_delete_route_not_found(self, client):
        """Test deal deletion with non-existent ID"""
        response = client.delete('/deals/99999', headers={'Accept': 'application/json'})
        assert response.status_code == 404
        
        data = response.get_json()
        assert 'error' in data
        assert data['error'] == 'Deal not found'

    def test_schedule_meeting_route_get(self, client, sample_data):
        """Test meeting scheduling interface"""
        # Get a deal ID from sample data
        deals = database_service.get_deals()
        assert len(deals) > 0
        deal_id = deals[0].id
        
        response = client.get(f'/deals/{deal_id}/schedule-meeting')
        assert response.status_code == 200
        assert b'Schedule Meeting' in response.data
        assert b'meeting_title' in response.data

    def test_schedule_meeting_route_not_found(self, client):
        """Test meeting scheduling with non-existent deal"""
        response = client.get('/deals/99999/schedule-meeting')
        assert response.status_code == 302  # Redirect on error

    def test_send_email_route_get(self, client, sample_data):
        """Test email composition interface"""
        # Get a deal ID from sample data
        deals = database_service.get_deals()
        assert len(deals) > 0
        deal_id = deals[0].id
        
        response = client.get(f'/deals/{deal_id}/send-email')
        assert response.status_code == 200
        assert b'Compose Email' in response.data
        assert b'recipient' in response.data

    def test_send_email_route_post(self, client, sample_data):
        """Test email sending"""
        # Get a deal ID from sample data
        deals = database_service.get_deals()
        assert len(deals) > 0
        deal_id = deals[0].id
        
        # Test email sending
        response = client.post(f'/deals/{deal_id}/send-email', data={
            'recipient': 'test@example.com',
            'subject': 'Test Subject',
            'message': 'Test message content'
        }, headers={'Accept': 'application/json'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'sent successfully' in data['message']

    def test_send_email_route_validation_error(self, client, sample_data):
        """Test email sending with missing fields"""
        # Get a deal ID from sample data
        deals = database_service.get_deals()
        assert len(deals) > 0
        deal_id = deals[0].id
        
        # Test with missing fields
        response = client.post(f'/deals/{deal_id}/send-email', data={
            'recipient': 'test@example.com',
            # Missing subject and message
        }, headers={'Accept': 'application/json'})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_export_deals_json(self, client, sample_data):
        """Test deals export in JSON format"""
        response = client.get('/deals/export?format=json')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'generated_at' in data
        assert 'summary' in data
        assert 'deals' in data
        assert isinstance(data['deals'], list)

    def test_export_deals_csv(self, client, sample_data):
        """Test deals export in CSV format"""
        response = client.get('/deals/export?format=csv')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'csv_content' in data
        assert 'Deal ID' in data['csv_content']  # CSV header

    def test_export_deals_invalid_format(self, client):
        """Test deals export with invalid format"""
        response = client.get('/deals/export?format=invalid')
        assert response.status_code == 400
        
        data = response.get_json()
        assert 'error' in data
        assert 'Unsupported export format' in data['error']

    def test_deal_routes_html_fallback(self, client, sample_data):
        """Test HTML fallback for deal routes"""
        # Get a deal ID from sample data
        deals = database_service.get_deals()
        assert len(deals) > 0
        deal_id = deals[0].id
        
        # Test HTML response (no JSON accept header)
        response = client.get(f'/deals/{deal_id}')
        assert response.status_code == 200
        assert b'Deal Details' in response.data or response.status_code == 302

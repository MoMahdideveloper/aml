"""
Integration tests for enhanced property routes with error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
import json

from views.properties import bp as properties_bp
from property_error_handlers import PropertyNotFoundError, PropertyValidationError


class TestEnhancedPropertyRoutes:
    """Test enhanced property routes with error handling"""
    
    def setup_method(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        self.app.register_blueprint(properties_bp)
        self.client = self.app.test_client()
        
        # Mock database and services
        self.mock_db_service = Mock()
        self.mock_property = Mock()
        self.mock_property.id = 123
        self.mock_property.title = "Test Property"
        self.mock_property.address = "123 Test St"
        self.mock_property.price = 100000
        self.mock_property.property_type = "house"
        self.mock_property.bedrooms = 3
        self.mock_property.bathrooms = 2
        self.mock_property.square_feet = 1500
        self.mock_property.description = "Test description"
        self.mock_property.status = "active"
        self.mock_property.year_built = 2020
        self.mock_property.parking_spaces = 2
        self.mock_property.floors = 2
        self.mock_property.units = 1
        self.mock_property.property_condition = "good"
        self.mock_property.neighborhood = "Test Neighborhood"
        self.mock_property.property_category = "residential"
        self.mock_property.listing_type = "sale"
        self.mock_property.rahn = None
        self.mock_property.ejare = None
        self.mock_property.property_features = "Test features"
        self.mock_property.created_at = Mock()
        self.mock_property.created_at.strftime.return_value = "2024-01-01 12:00:00"
        self.mock_property.agent = Mock()
        self.mock_property.agent.name = "Test Agent"
        self.mock_property.agent.email = "agent@test.com"
        self.mock_property.agent.phone = "123-456-7890"
        self.mock_property.agent_id = 1
        self.mock_property.deals = []
    
    @patch('views.properties.get_property_with_related_data')
    def test_property_detail_success(self, mock_get_property):
        """Test successful property detail page load"""
        mock_get_property.return_value = self.mock_property
        
        response = self.client.get('/properties/123/detail')
        
        assert response.status_code == 200
        mock_get_property.assert_called_once_with(123)
    
    @patch('views.properties.get_property_with_related_data')
    def test_property_detail_not_found(self, mock_get_property):
        """Test property detail page with non-existent property"""
        mock_get_property.side_effect = PropertyNotFoundError(999)
        
        response = self.client.get('/properties/999/detail')
        
        # Should redirect to properties list
        assert response.status_code == 302
        assert '/properties' in response.location
    
    def test_property_detail_invalid_id(self):
        """Test property detail page with invalid property ID"""
        response = self.client.get('/properties/invalid/detail')
        
        # Should return 404 for invalid ID format
        assert response.status_code == 404
    
    @patch('views.properties.database_service')
    def test_view_property_modal_success_ajax(self, mock_db_service):
        """Test successful property view modal for AJAX request"""
        mock_db_service.get_property.return_value = self.mock_property
        
        response = self.client.get(
            '/properties/123',
            headers={'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'property' in data
        assert data['property']['id'] == 123
        assert data['property']['title'] == "Test Property"
    
    @patch('views.properties.database_service')
    def test_view_property_modal_not_found_ajax(self, mock_db_service):
        """Test property view modal with non-existent property for AJAX"""
        mock_db_service.get_property.return_value = None
        
        response = self.client.get(
            '/properties/999',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('views.properties.database_service')
    def test_edit_property_success_ajax(self, mock_db_service):
        """Test successful property edit form load for AJAX"""
        mock_db_service.get_property.return_value = self.mock_property
        
        response = self.client.get(
            '/properties/123/edit',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'property' in data
        assert data['property']['id'] == 123
    
    @patch('views.properties.database_service')
    def test_update_property_success_ajax(self, mock_db_service):
        """Test successful property update for AJAX request"""
        mock_db_service.get_property.return_value = self.mock_property
        mock_db_service.update_property.return_value = self.mock_property
        
        update_data = {
            'title': 'Updated Property',
            'address': '456 Updated St',
            'property_type': 'condo',
            'listing_type': 'sale',
            'sale_price': '150000',
            'bedrooms': '2',
            'bathrooms': '1',
            'square_feet': '1200'
        }
        
        response = self.client.post(
            '/properties/123',
            data=update_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'property' in data
        assert 'message' in data

    @patch('views.properties.database_service')
    def test_update_property_accepts_comma_separated_sale_price(self, mock_db_service):
        """Sale pricing should accept comma-formatted numbers."""
        mock_db_service.get_property.return_value = self.mock_property
        mock_db_service.update_property.return_value = self.mock_property

        update_data = {
            'title': 'Updated Property',
            'address': '456 Updated St',
            'property_type': 'condo',
            'listing_type': 'sale',
            'sale_price': '150,000',
            'bedrooms': '2',
            'bathrooms': '1',
            'square_feet': '1200'
        }

        response = self.client.post(
            '/properties/123',
            data=update_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )

        assert response.status_code == 200
        assert mock_db_service.update_property.called
        assert mock_db_service.update_property.call_args.kwargs.get('price') == 150000

    @patch('views.properties.database_service')
    def test_update_property_allows_zero_square_feet(self, mock_db_service):
        """Test property update accepts square_feet=0 and forwards non-negative value."""
        mock_db_service.get_property.return_value = self.mock_property
        mock_db_service.update_property.return_value = self.mock_property

        update_data = {
            'title': 'Updated Property',
            'address': '456 Updated St',
            'property_type': 'condo',
            'listing_type': 'sale',
            'sale_price': '150000',
            'bedrooms': '2',
            'bathrooms': '1',
            'square_feet': '0'
        }

        response = self.client.post(
            '/properties/123',
            data=update_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )

        assert response.status_code == 200
        assert mock_db_service.update_property.called
        assert mock_db_service.update_property.call_args.kwargs.get('square_feet') == 0
    
    @patch('views.properties.database_service')
    def test_update_property_validation_error(self, mock_db_service):
        """Test property update with validation errors"""
        mock_db_service.get_property.return_value = self.mock_property
        
        # Missing required fields
        update_data = {
            'title': '',  # Empty title should fail validation
            'address': '456 Updated St',
            'property_type': 'condo'
        }
        
        response = self.client.post(
            '/properties/123',
            data=update_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('views.properties.database_service')
    def test_update_property_invalid_price(self, mock_db_service):
        """Test property update with invalid price data"""
        mock_db_service.get_property.return_value = self.mock_property
        
        update_data = {
            'title': 'Updated Property',
            'address': '456 Updated St',
            'property_type': 'condo',
            'listing_type': 'sale',
            'sale_price': 'invalid_price',  # Invalid price format
            'bedrooms': '2',
            'bathrooms': '1',
            'square_feet': '1200'
        }
        
        response = self.client.post(
            '/properties/123',
            data=update_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'error' in data
        assert 'pricing data' in data['error'].lower()
    
    @patch('views.properties.database_service')
    def test_update_property_rental_validation(self, mock_db_service):
        """Test property update with rental property validation"""
        mock_db_service.get_property.return_value = self.mock_property
        
        # Test rental property without rahn or ejare
        update_data = {
            'title': 'Rental Property',
            'address': '789 Rental St',
            'property_type': 'apartment',
            'listing_type': 'rental',
            'bedrooms': '2',
            'bathrooms': '1',
            'square_feet': '1000'
            # Missing rahn and ejare
        }
        
        response = self.client.post(
            '/properties/123',
            data=update_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'error' in data
        assert 'rahn or ejare' in data['error'].lower()
    
    @patch('views.properties.database_service')
    def test_update_property_rental_success(self, mock_db_service):
        """Test successful rental property update"""
        mock_db_service.get_property.return_value = self.mock_property
        mock_db_service.update_property.return_value = self.mock_property
        
        update_data = {
            'title': 'Rental Property',
            'address': '789 Rental St',
            'property_type': 'apartment',
            'listing_type': 'rental',
            'rahn': '50000000',  # Valid rahn amount
            'ejare': '2000000',  # Valid ejare amount
            'bedrooms': '2',
            'bathrooms': '1',
            'square_feet': '1000'
        }
        
        response = self.client.post(
            '/properties/123',
            data=update_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'property' in data
        assert 'message' in data

    @patch('views.properties.database_service')
    def test_update_property_rental_accepts_comma_formatted_prices(self, mock_db_service):
        """Rental pricing should accept comma-formatted toman amounts."""
        mock_db_service.get_property.return_value = self.mock_property
        mock_db_service.update_property.return_value = self.mock_property

        update_data = {
            'title': 'Rental Property',
            'address': '789 Rental St',
            'property_type': 'apartment',
            'listing_type': 'rental',
            'rahn': '50,000,000',
            'ejare': '2,000,000',
            'bedrooms': '2',
            'bathrooms': '1',
            'square_feet': '1000'
        }

        response = self.client.post(
            '/properties/123',
            data=update_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )

        assert response.status_code == 200
        assert mock_db_service.update_property.called
        assert mock_db_service.update_property.call_args.kwargs.get('rahn') == 50000000
        assert mock_db_service.update_property.call_args.kwargs.get('ejare') == 2000000
    
    @patch('views.properties.database_service')
    def test_update_property_numeric_validation(self, mock_db_service):
        """Test property update with invalid numeric values"""
        mock_db_service.get_property.return_value = self.mock_property
        
        update_data = {
            'title': 'Test Property',
            'address': '123 Test St',
            'property_type': 'house',
            'listing_type': 'sale',
            'sale_price': '100000',
            'bedrooms': '-1',  # Invalid negative bedrooms
            'bathrooms': '1',
            'square_feet': '1000'
        }
        
        response = self.client.post(
            '/properties/123',
            data=update_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'error' in data
        assert 'bedrooms' in data['error'].lower()
    
    @patch('views.properties.database_service')
    def test_update_property_year_built_validation(self, mock_db_service):
        """Test property update with invalid year built"""
        mock_db_service.get_property.return_value = self.mock_property
        
        update_data = {
            'title': 'Test Property',
            'address': '123 Test St',
            'property_type': 'house',
            'listing_type': 'sale',
            'sale_price': '100000',
            'bedrooms': '3',
            'bathrooms': '2',
            'square_feet': '1500',
            'year_built': '1700'  # Invalid year (too old)
        }
        
        response = self.client.post(
            '/properties/123',
            data=update_data,
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        assert response.status_code == 422
        data = json.loads(response.data)
        assert 'error' in data
        assert 'year built' in data['error'].lower()
    
    @patch('views.properties.database_service')
    def test_property_database_error_handling(self, mock_db_service):
        """Test handling of database errors"""
        from sqlalchemy.exc import SQLAlchemyError
        mock_db_service.get_property.side_effect = SQLAlchemyError("Database error", None, None)
        
        response = self.client.get(
            '/properties/123',
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_property_id_validation_edge_cases(self):
        """Test property ID validation with edge cases"""
        # Test with zero
        response = self.client.get('/properties/0/detail')
        assert response.status_code == 400
        
        # Test with negative number
        response = self.client.get('/properties/-1/detail')
        assert response.status_code == 400
        
        # Test with very large number (should still work)
        with patch('views.properties.get_property_with_related_data') as mock_get:
            mock_get.side_effect = PropertyNotFoundError(999999999)
            response = self.client.get('/properties/999999999/detail')
            assert response.status_code == 302  # Redirect due to not found
    
    @patch('views.properties.Property')
    def test_related_properties_error_handling(self, mock_property_model):
        """Test that related properties errors don't break the main page"""
        # Mock the main property fetch to succeed
        with patch('views.properties.get_property_with_related_data') as mock_get:
            mock_get.return_value = self.mock_property
            
            # Mock related properties query to fail
            mock_query = Mock()
            mock_query.filter.side_effect = Exception("Related properties error")
            mock_property_model.query = mock_query
            
            response = self.client.get('/properties/123/detail')
            
            # Should still succeed despite related properties error
            assert response.status_code == 200
    
    @patch('views.properties.database_service')
    def test_property_with_missing_agent(self, mock_db_service):
        """Test property handling when agent is missing"""
        # Create property without agent
        property_without_agent = Mock()
        property_without_agent.id = 123
        property_without_agent.title = "Test Property"
        property_without_agent.agent = None
        property_without_agent.agent_id = None
        property_without_agent.deals = []
        # Set other required attributes
        for attr in ['address', 'price', 'property_type', 'bedrooms', 'bathrooms', 
                     'square_feet', 'description', 'status', 'year_built', 'parking_spaces',
                     'floors', 'units', 'property_condition', 'neighborhood', 
                     'property_category', 'listing_type', 'rahn', 'ejare', 
                     'property_features', 'created_at']:
            setattr(property_without_agent, attr, None)
        
        mock_db_service.get_property.return_value = property_without_agent
        
        response = self.client.get(
            '/properties/123',
            headers={'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json'}
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['property']['agent_name'] == 'Unassigned'
        assert data['property']['agent_email'] == ''


if __name__ == '__main__':
    pytest.main([__file__])

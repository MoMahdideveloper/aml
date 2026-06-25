"""
Unit tests for enhanced database service methods
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from services.database_service import DatabaseService, database_service
from sqlalchemy_models import Property, Agent


class TestEnhancedDatabaseService:
    """Test enhanced database service methods"""
    
    def setup_method(self, method):
        """Set up test environment"""
        from app import app
        from database import db
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        self.db_service = DatabaseService()
        
        # Mock property data
        self.mock_property_data = {
            'title': 'Test Property',
            'address': '123 Test St',
            'price': 100000,
            'property_type': 'house',
            'bedrooms': 3,
            'bathrooms': 2,
            'square_feet': 1500,
            'description': 'Test description',
            'status': 'active',
            'agent_id': 1,
            'year_built': 2020,
            'parking_spaces': 2,
            'floors': 2,
            'units': 1,
            'property_condition': 'good',
            'neighborhood': 'Test Neighborhood',
            'property_category': 'residential',
            'listing_type': 'sale'
        }
    
    def teardown_method(self, method):
        """Clean up test environment"""
        if hasattr(self, 'app_context'):
            from database import db
            db.session.remove()
            db.drop_all()
            self.app_context.pop()
    
    @patch('services.database_service.db')
    @patch('services.database_service.Agent')
    def test_create_property_with_validation_success(self, mock_agent_model, mock_db):
        """Test successful property creation with validation"""
        # Mock agent exists
        mock_agent = Mock()
        mock_db.session.get.return_value = mock_agent
        
        # Mock property creation
        mock_property = Mock()
        mock_property.id = 123
        mock_db.session.add.return_value = None
        mock_db.session.flush.return_value = None
        
        with patch('services.database_service.Property') as mock_property_class:
            mock_property_class.return_value = mock_property
            
            result = self.db_service.create_property_with_validation(**self.mock_property_data)
            
            assert result == mock_property
            mock_db.session.add.assert_called_once()
            mock_db.session.flush.assert_called_once()
    
    def test_create_property_with_validation_missing_title(self):
        """Test property creation with missing title"""
        data = self.mock_property_data.copy()
        data['title'] = ''
        
        with pytest.raises(ValueError, match="Property title is required"):
            self.db_service.create_property_with_validation(**data)
    
    def test_create_property_with_validation_missing_address(self):
        """Test property creation with missing address"""
        data = self.mock_property_data.copy()
        data['address'] = ''
        
        with pytest.raises(ValueError, match="Property address is required"):
            self.db_service.create_property_with_validation(**data)
    
    def test_create_property_with_validation_negative_price(self):
        """Test property creation with negative price"""
        data = self.mock_property_data.copy()
        data['price'] = -1000
        
        with pytest.raises(ValueError, match="Price cannot be negative"):
            self.db_service.create_property_with_validation(**data)
    
    def test_create_property_with_validation_invalid_bedrooms(self):
        """Test property creation with invalid bedrooms"""
        data = self.mock_property_data.copy()
        data['bedrooms'] = -1
        
        with pytest.raises(ValueError, match="Bedrooms must be between 0 and 50"):
            self.db_service.create_property_with_validation(**data)
        
        data['bedrooms'] = 51
        with pytest.raises(ValueError, match="Bedrooms must be between 0 and 50"):
            self.db_service.create_property_with_validation(**data)
    
    def test_create_property_with_validation_invalid_year_built(self):
        """Test property creation with invalid year built"""
        data = self.mock_property_data.copy()
        data['year_built'] = 1700
        
        with pytest.raises(ValueError, match="Year built must be between 1800 and 2030"):
            self.db_service.create_property_with_validation(**data)
    
    @patch('services.database_service.db')
    def test_create_property_with_validation_nonexistent_agent(self, mock_db):
        """Test property creation with non-existent agent"""
        mock_db.session.get.return_value = None  # Agent not found
        
        with pytest.raises(ValueError, match="Agent with ID 1 not found"):
            self.db_service.create_property_with_validation(**self.mock_property_data)
    
    @patch('services.database_service.db')
    def test_create_property_with_validation_rental_missing_amounts(self, mock_db):
        """Test rental property creation without rahn or ejare"""
        # Mock agent exists
        mock_db.session.get.return_value = Mock()
        data = self.mock_property_data.copy()
        data['listing_type'] = 'rental'
        data['rahn'] = None
        data['ejare'] = None
        
        with pytest.raises(ValueError, match="Either Rahn or Ejare is required for rental properties"):
            self.db_service.create_property_with_validation(**data)
    
    @patch('services.database_service.db')
    def test_create_property_with_validation_rental_negative_rahn(self, mock_db):
        """Test rental property creation with negative rahn"""
        # Mock agent exists
        mock_db.session.get.return_value = Mock()
        data = self.mock_property_data.copy()
        data['listing_type'] = 'rental'
        data['rahn'] = -1000
        data['ejare'] = 500000
        
        with pytest.raises(ValueError, match="Rahn amount cannot be negative"):
            self.db_service.create_property_with_validation(**data)
    
    @patch('services.database_service.db')
    def test_create_property_with_validation_sale_zero_price(self, mock_db):
        """Test sale property creation with zero price"""
        # Mock agent exists
        mock_db.session.get.return_value = Mock()
        data = self.mock_property_data.copy()
        data['listing_type'] = 'sale'
        data['price'] = 0
        
        with pytest.raises(ValueError, match="Sale price must be greater than zero"):
            self.db_service.create_property_with_validation(**data)
    
    @patch('services.database_service.db')
    def test_update_property_with_validation_success(self, mock_db):
        """Test successful property update with validation"""
        mock_property = Mock()
        mock_property.title = 'Old Title'
        mock_property.price = 100000
        mock_db.session.get.return_value = mock_property
        
        updates = {'title': 'New Title', 'price': 150000}
        result = self.db_service.update_property_with_validation(123, **updates)
        
        assert result == mock_property
        assert mock_property.title == 'New Title'
        assert mock_property.price == 150000
    
    @patch('services.database_service.db')
    def test_update_property_with_validation_not_found(self, mock_db):
        """Test property update with non-existent property"""
        mock_db.session.get.return_value = None
        
        with pytest.raises(ValueError, match="Property with ID 999 not found"):
            self.db_service.update_property_with_validation(999, title='New Title')
    
    @patch('services.database_service.db')
    def test_update_property_with_validation_empty_title(self, mock_db):
        """Test property update with empty title"""
        mock_property = Mock()
        mock_property.title = 'Old Title'
        mock_db.session.get.return_value = mock_property
        
        with pytest.raises(ValueError, match="Property title cannot be empty"):
            self.db_service.update_property_with_validation(123, title='')
    
    @patch('services.database_service.db')
    def test_update_property_with_validation_invalid_agent(self, mock_db):
        """Test property update with non-existent agent"""
        mock_property = Mock()
        mock_property.agent_id = 1
        mock_db.session.get.side_effect = [mock_property, None]  # Property exists, agent doesn't
        
        with pytest.raises(ValueError, match="Agent with ID 999 not found"):
            self.db_service.update_property_with_validation(123, agent_id=999)
    
    @patch('services.database_service.db')
    def test_delete_property_with_validation_success(self, mock_db):
        """Test successful property deletion"""
        mock_property = Mock()
        mock_property.title = 'Test Property'
        mock_property.deals = []
        mock_db.session.get.return_value = mock_property
        
        result = self.db_service.delete_property_with_validation(123)
        
        assert result is True
        mock_db.session.delete.assert_called_once_with(mock_property)
    
    @patch('services.database_service.db')
    def test_delete_property_with_validation_not_found(self, mock_db):
        """Test property deletion with non-existent property"""
        mock_db.session.get.return_value = None
        
        with pytest.raises(ValueError, match="Property with ID 999 not found"):
            self.db_service.delete_property_with_validation(999)
    
    @patch('services.database_service.db')
    def test_delete_property_with_validation_active_deals(self, mock_db):
        """Test property deletion with active deals"""
        mock_deal = Mock()
        mock_deal.status = 'active'
        
        mock_property = Mock()
        mock_property.title = 'Test Property'
        mock_property.deals = [mock_deal]
        mock_db.session.get.return_value = mock_property
        
        with pytest.raises(ValueError, match="Cannot delete property - it has 1 active deal"):
            self.db_service.delete_property_with_validation(123)
    
    @patch('services.database_service.db')
    def test_delete_property_with_validation_force_delete(self, mock_db):
        """Test forced property deletion with active deals"""
        mock_deal = Mock()
        mock_deal.status = 'active'
        
        mock_property = Mock()
        mock_property.title = 'Test Property'
        mock_property.deals = [mock_deal]
        mock_db.session.get.return_value = mock_property
        
        result = self.db_service.delete_property_with_validation(123, force=True)
        
        assert result is True
        mock_db.session.delete.assert_called_once_with(mock_property)
    
    @patch('services.database_service.DatabaseService.get_property_with_validation')
    def test_get_property_statistics_success(self, mock_get_property):
        """Test successful property statistics calculation"""
        # Mock property with deals
        mock_deal1 = Mock()
        mock_deal1.status = 'active'
        mock_deal1.value = 100000
        mock_deal1.updated_at = datetime.now()
        mock_deal1.created_at = datetime.now() - timedelta(days=5)
        
        mock_deal2 = Mock()
        mock_deal2.status = 'closed_won'
        mock_deal2.value = 150000
        mock_deal2.updated_at = datetime.now() - timedelta(days=2)
        mock_deal2.created_at = datetime.now() - timedelta(days=10)
        
        mock_property = Mock()
        mock_property.created_at = datetime.utcnow() - timedelta(days=30)
        mock_property.deals = [mock_deal1, mock_deal2]
        
        mock_get_property.return_value = mock_property
        
        stats = self.db_service.get_property_statistics(123)
        
        assert stats['property_id'] == 123
        assert stats['total_deals'] == 2
        assert stats['active_deals'] == 1
        assert stats['won_deals'] == 1
        assert stats['total_deal_value'] == 250000
        assert stats['average_deal_value'] == 125000
        assert stats['days_on_market'] == 30
    
    @patch('services.database_service.DatabaseService.get_property_with_validation')
    def test_get_property_statistics_no_property(self, mock_get_property):
        """Test property statistics with non-existent property"""
        mock_get_property.return_value = None
        
        stats = self.db_service.get_property_statistics(999)
        
        assert stats == {}
    
    @patch('services.database_service.Property')
    def test_search_properties_advanced_success(self, mock_property_model):
        """Test advanced property search"""
        # Mock query chain
        mock_query = Mock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        # Mock pagination
        mock_pagination = Mock()
        mock_pagination.items = []
        mock_pagination.total = 0
        mock_pagination.pages = 0
        mock_pagination.has_next = False
        mock_pagination.has_prev = False
        mock_pagination.next_num = None
        mock_pagination.prev_num = None
        mock_query.paginate.return_value = mock_pagination
        
        mock_property_model.query = mock_query
        
        filters = {
            'property_type': 'house',
            'min_price': 100000,
            'max_price': 500000
        }
        
        result = self.db_service.search_properties_advanced(
            search_query='test',
            filters=filters,
            sort_by='price',
            sort_order='asc',
            page=1,
            per_page=10
        )
        
        assert 'properties' in result
        assert 'total' in result
        assert 'pages' in result
        assert result['current_page'] == 1
        assert result['per_page'] == 10
    
    @patch('services.database_service.Property')
    def test_search_properties_advanced_error(self, mock_property_model):
        """Test advanced property search with error"""
        mock_property_model.query.options.side_effect = Exception("Database error")
        
        result = self.db_service.search_properties_advanced()
        
        assert result['properties'] == []
        assert result['total'] == 0
        assert 'error' in result
    
    @patch('services.database_service.DatabaseService.update_property_with_validation')
    @patch('services.database_service.database_transaction')
    def test_bulk_update_properties_success(self, mock_transaction, mock_update):
        """Test successful bulk property update"""
        # Mock successful updates
        mock_property1 = Mock()
        mock_property1.title = 'Property 1'
        mock_property2 = Mock()
        mock_property2.title = 'Property 2'
        
        mock_update.side_effect = [mock_property1, mock_property2]
        mock_transaction.return_value.__enter__ = Mock()
        mock_transaction.return_value.__exit__ = Mock(return_value=None)
        
        property_ids = [1, 2]
        updates = {'status': 'inactive'}
        
        result = self.db_service.bulk_update_properties(property_ids, updates)
        
        assert result['total_requested'] == 2
        assert result['total_updated'] == 2
        assert result['total_failed'] == 0
        assert len(result['updated']) == 2
        assert len(result['failed']) == 0
    
    @patch('services.database_service.DatabaseService.update_property_with_validation')
    @patch('services.database_service.database_transaction')
    def test_bulk_update_properties_partial_failure(self, mock_transaction, mock_update):
        """Test bulk property update with partial failures"""
        mock_property1 = Mock()
        mock_property1.title = 'Property 1'
        
        mock_update.side_effect = [mock_property1, ValueError("Property not found")]
        mock_transaction.return_value.__enter__ = Mock()
        mock_transaction.return_value.__exit__ = Mock(return_value=None)
        
        property_ids = [1, 2]
        updates = {'status': 'inactive'}
        
        result = self.db_service.bulk_update_properties(property_ids, updates)
        
        assert result['total_requested'] == 2
        assert result['total_updated'] == 1
        assert result['total_failed'] == 1
        assert len(result['updated']) == 1
        assert len(result['failed']) == 1
    
    @patch('services.database_service.DatabaseService.get_property')
    def test_get_property_history_success(self, mock_get_property):
        """Test property history retrieval"""
        mock_property = Mock()
        mock_property.title = 'Test Property'
        mock_property.created_at = datetime.now() - timedelta(days=10)
        mock_property.updated_at = datetime.now() - timedelta(days=5)
        
        mock_get_property.return_value = mock_property
        
        history = self.db_service.get_property_history(123)
        
        assert len(history) == 2
        assert history[0]['action'] == 'updated'  # Most recent first
        assert history[1]['action'] == 'created'
    
    @patch('services.database_service.DatabaseService.get_property')
    def test_get_property_history_no_property(self, mock_get_property):
        """Test property history with non-existent property"""
        mock_get_property.return_value = None
        
        history = self.db_service.get_property_history(999)
        
        assert history == []
    
    def test_validation_edge_cases(self):
        """Test validation edge cases"""
        # Test maximum valid values
        data = self.mock_property_data.copy()
        data.update({
            'bedrooms': 50,
            'bathrooms': 50,
            'square_feet': 10000000,
            'year_built': 2030,
            'parking_spaces': 100,
            'floors': 200,
            'units': 10000
        })
        
        # Should not raise any exceptions for maximum valid values
        with patch('services.database_service.db') as mock_db:
            mock_agent = Mock()
            mock_db.session.get.return_value = mock_agent
            
            with patch('services.database_service.Property') as mock_property_class:
                mock_property = Mock()
                mock_property.id = 123
                mock_property_class.return_value = mock_property
                
                result = self.db_service.create_property_with_validation(**data)
                assert result == mock_property
    
    def test_string_field_trimming(self):
        """Test that string fields are properly trimmed"""
        data = self.mock_property_data.copy()
        data.update({
            'title': '  Test Property  ',
            'address': '  123 Test St  ',
            'description': '  Test description  ',
            'neighborhood': '  Test Neighborhood  ',
            'property_features': '  Test features  '
        })
        
        with patch('services.database_service.db') as mock_db:
            mock_agent = Mock()
            mock_db.session.get.return_value = mock_agent
            
            with patch('services.database_service.Property') as mock_property_class:
                mock_property = Mock()
                mock_property.id = 123
                mock_property_class.return_value = mock_property
                
                result = self.db_service.create_property_with_validation(**data)
                
                # Verify trimming was applied
                assert mock_property.title == 'Test Property'
                assert mock_property.address == '123 Test St'
                assert mock_property.description == 'Test description'
                assert mock_property.neighborhood == 'Test Neighborhood'
                assert mock_property.property_features == 'Test features'


if __name__ == '__main__':
    pytest.main([__file__])

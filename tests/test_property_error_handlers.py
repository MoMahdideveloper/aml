"""
Unit tests for property error handling decorators and utilities
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, request, jsonify
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from property_error_handlers import (
    PropertyError, PropertyNotFoundError, PropertyValidationError, PropertyOperationError,
    validate_property_id, handle_property_errors, require_property_exists,
    validate_property_data, handle_database_connection_error,
    safe_get_property, get_property_with_related_data
)


class TestPropertyErrorClasses:
    """Test custom property error classes"""
    
    def test_property_error_base(self):
        """Test base PropertyError class"""
        error = PropertyError("Test error", status_code=400, details={'key': 'value'})
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.details == {'key': 'value'}
    
    def test_property_not_found_error(self):
        """Test PropertyNotFoundError"""
        error = PropertyNotFoundError(123)
        assert "Property with ID 123 not found" in error.message
        assert error.status_code == 404
        assert error.details['property_id'] == 123
        
        # Test with custom message
        error = PropertyNotFoundError(456, "Custom not found message")
        assert error.message == "Custom not found message"
        assert error.details['property_id'] == 456
    
    def test_property_validation_error(self):
        """Test PropertyValidationError"""
        validation_errors = {'title': 'Title is required', 'price': 'Invalid price'}
        error = PropertyValidationError("Validation failed", validation_errors)
        assert error.message == "Validation failed"
        assert error.status_code == 422
        assert error.details['validation_errors'] == validation_errors
    
    def test_property_operation_error(self):
        """Test PropertyOperationError"""
        error = PropertyOperationError("Operation failed", operation="update_property")
        assert error.message == "Operation failed"
        assert error.status_code == 500
        assert error.details['operation'] == "update_property"


class TestValidatePropertyIdDecorator:
    """Test validate_property_id decorator"""
    
    def test_valid_property_id(self):
        """Test decorator with valid property ID"""
        @validate_property_id
        def test_func(property_id):
            return f"Property ID: {property_id}"
        
        result = test_func(property_id=123)
        assert result == "Property ID: 123"
    
    def test_invalid_property_id_string(self):
        """Test decorator with invalid string property ID"""
        @validate_property_id
        def test_func(property_id):
            return f"Property ID: {property_id}"
        
        with pytest.raises(Exception):  # Should raise BadRequest
            test_func(property_id="invalid")
    
    def test_negative_property_id(self):
        """Test decorator with negative property ID"""
        @validate_property_id
        def test_func(property_id):
            return f"Property ID: {property_id}"
        
        with pytest.raises(Exception):  # Should raise BadRequest
            test_func(property_id=-1)
    
    def test_missing_property_id(self):
        """Test decorator with missing property ID"""
        @validate_property_id
        def test_func(property_id=None):
            return f"Property ID: {property_id}"
        
        with pytest.raises(Exception):  # Should raise BadRequest
            test_func()


class TestHandlePropertyErrorsDecorator:
    """Test handle_property_errors decorator"""
    
    def setup_method(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
    
    def test_successful_execution(self):
        """Test decorator with successful function execution"""
        @handle_property_errors
        def test_func():
            return "Success"
        
        with self.app.test_request_context():
            result = test_func()
            assert result == "Success"
    
    def test_property_not_found_error_ajax(self):
        """Test handling PropertyNotFoundError for AJAX requests"""
        @handle_property_errors
        def test_func():
            raise PropertyNotFoundError(123)
        
        with self.app.test_request_context(headers={'X-Requested-With': 'XMLHttpRequest'}):
            response, status_code = test_func()
            assert status_code == 404
            assert 'Property with ID 123 not found' in response.get_data(as_text=True)
    
    def test_property_validation_error(self):
        """Test handling PropertyValidationError"""
        @handle_property_errors
        def test_func():
            raise PropertyValidationError("Validation failed", {'title': 'Required'})
        
        with self.app.test_request_context(headers={'X-Requested-With': 'XMLHttpRequest'}):
            response, status_code = test_func()
            assert status_code == 422
            assert 'Validation failed' in response.get_data(as_text=True)
    
    @patch('property_error_handlers.db')
    def test_integrity_error_handling(self, mock_db):
        """Test handling SQLAlchemy IntegrityError"""
        @handle_property_errors
        def test_func():
            raise IntegrityError("statement", "params", "orig")
        
        with self.app.test_request_context(headers={'X-Requested-With': 'XMLHttpRequest'}):
            response, status_code = test_func()
            assert status_code == 500
            assert 'Data integrity error' in response.get_data(as_text=True)
            mock_db.session.rollback.assert_called_once()
    
    @patch('property_error_handlers.db')
    def test_unexpected_error_handling(self, mock_db):
        """Test handling unexpected errors"""
        @handle_property_errors
        def test_func():
            raise Exception("Unexpected error")
        
        with self.app.test_request_context(headers={'X-Requested-With': 'XMLHttpRequest'}):
            response, status_code = test_func()
            assert status_code == 500
            assert 'unexpected error occurred' in response.get_data(as_text=True)
            mock_db.session.rollback.assert_called_once()


class TestRequirePropertyExistsDecorator:
    """Test require_property_exists decorator"""
    
    def setup_method(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
    
    @patch('property_error_handlers.database_service')
    def test_property_exists(self, mock_db_service):
        """Test decorator when property exists"""
        mock_property = Mock()
        mock_property.id = 123
        mock_db_service.get_property.return_value = mock_property
        
        @require_property_exists
        def test_func(property_id, property_obj):
            return f"Property: {property_obj.id}"
        
        with self.app.test_request_context():
            result = test_func(property_id=123)
            assert result == "Property: 123"
            mock_db_service.get_property.assert_called_once_with(123)
    
    @patch('property_error_handlers.database_service')
    def test_property_not_exists(self, mock_db_service):
        """Test decorator when property doesn't exist"""
        mock_db_service.get_property.return_value = None
        
        @require_property_exists
        def test_func(property_id, property_obj):
            return f"Property: {property_obj.id}"
        
        with self.app.test_request_context():
            with pytest.raises(PropertyNotFoundError):
                test_func(property_id=123)


class TestValidatePropertyDataDecorator:
    """Test validate_property_data decorator"""
    
    def setup_method(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
    
    def test_valid_json_data(self):
        """Test decorator with valid JSON data"""
        @validate_property_data(required_fields=['title'], optional_fields=['price'])
        def test_func():
            return "Success"
        
        with self.app.test_request_context(
            json={'title': 'Test Property', 'price': '100000'}
        ):
            result = test_func()
            assert result == "Success"
    
    def test_missing_required_field(self):
        """Test decorator with missing required field"""
        @validate_property_data(required_fields=['title'])
        def test_func():
            return "Success"
        
        with self.app.test_request_context(json={}):
            with pytest.raises(PropertyValidationError) as exc_info:
                test_func()
            assert 'title is required' in str(exc_info.value)
    
    def test_invalid_price_format(self):
        """Test decorator with invalid price format"""
        @validate_property_data(required_fields=['title'])
        def test_func():
            return "Success"
        
        with self.app.test_request_context(
            json={'title': 'Test Property', 'price': 'invalid'}
        ):
            with pytest.raises(PropertyValidationError) as exc_info:
                test_func()
            assert 'Price must be a valid number' in str(exc_info.value)
    
    def test_negative_bedrooms(self):
        """Test decorator with negative bedrooms"""
        @validate_property_data(required_fields=['title'])
        def test_func():
            return "Success"
        
        with self.app.test_request_context(
            json={'title': 'Test Property', 'bedrooms': '-1'}
        ):
            with pytest.raises(PropertyValidationError) as exc_info:
                test_func()
            assert 'Bedrooms must be non-negative' in str(exc_info.value)

    def test_zero_square_feet_is_allowed(self):
        """Test decorator allows square_feet=0 (non-negative rule)."""
        @validate_property_data(required_fields=['title'])
        def test_func():
            return "Success"

        with self.app.test_request_context(
            json={'title': 'Test Property', 'square_feet': '0'}
        ):
            result = test_func()
            assert result == "Success"

    def test_negative_square_feet_rejected(self):
        """Test decorator rejects negative square_feet values."""
        @validate_property_data(required_fields=['title'])
        def test_func():
            return "Success"

        with self.app.test_request_context(
            json={'title': 'Test Property', 'square_feet': '-1'}
        ):
            with pytest.raises(PropertyValidationError) as exc_info:
                test_func()
            assert 'Square feet must be non-negative' in str(exc_info.value)


class TestUtilityFunctions:
    """Test utility functions"""
    
    def setup_method(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
    
    @patch('property_error_handlers.database_service')
    def test_safe_get_property_success(self, mock_db_service):
        """Test safe_get_property with existing property"""
        mock_property = Mock()
        mock_property.id = 123
        mock_db_service.get_property.return_value = mock_property
        
        with self.app.test_request_context():
            result = safe_get_property(123)
            assert result.id == 123
    
    @patch('property_error_handlers.database_service')
    def test_safe_get_property_not_found(self, mock_db_service):
        """Test safe_get_property with non-existing property"""
        mock_db_service.get_property.return_value = None
        
        with self.app.test_request_context():
            with pytest.raises(PropertyNotFoundError):
                safe_get_property(123)
    
    @patch('property_error_handlers.database_service')
    def test_safe_get_property_database_error(self, mock_db_service):
        """Test safe_get_property with database error"""
        mock_db_service.get_property.side_effect = SQLAlchemyError("DB Error")
        
        with self.app.test_request_context():
            with pytest.raises(PropertyOperationError):
                safe_get_property(123)
    
    @patch('property_error_handlers.Property')
    def test_get_property_with_related_data_success(self, mock_property_model):
        """Test get_property_with_related_data with existing property"""
        mock_property = Mock()
        mock_property.id = 123
        mock_query = Mock()
        mock_query.options.return_value.filter_by.return_value.first.return_value = mock_property
        mock_property_model.query = mock_query
        
        with self.app.test_request_context():
            result = get_property_with_related_data(123)
            assert result.id == 123
    
    @patch('property_error_handlers.Property')
    def test_get_property_with_related_data_not_found(self, mock_property_model):
        """Test get_property_with_related_data with non-existing property"""
        mock_query = Mock()
        mock_query.options.return_value.filter_by.return_value.first.return_value = None
        mock_property_model.query = mock_query
        
        with self.app.test_request_context():
            with pytest.raises(PropertyNotFoundError):
                get_property_with_related_data(123)


class TestDatabaseConnectionErrorDecorator:
    """Test handle_database_connection_error decorator"""
    
    def setup_method(self):
        """Set up test environment"""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
    
    def test_successful_execution(self):
        """Test decorator with successful execution"""
        @handle_database_connection_error
        def test_func():
            return "Success"
        
        with self.app.test_request_context():
            result = test_func()
            assert result == "Success"
    
    def test_database_connection_error_ajax(self):
        """Test handling database connection error for AJAX"""
        @handle_database_connection_error
        def test_func():
            raise Exception("Connection timeout")
        
        with self.app.test_request_context(headers={'X-Requested-With': 'XMLHttpRequest'}):
            response, status_code = test_func()
            assert status_code == 503
            assert 'Database connection error' in response.get_data(as_text=True)
    
    def test_non_connection_error(self):
        """Test that non-connection errors are re-raised"""
        @handle_database_connection_error
        def test_func():
            raise ValueError("Not a connection error")
        
        with self.app.test_request_context():
            with pytest.raises(ValueError):
                test_func()


if __name__ == '__main__':
    pytest.main([__file__])

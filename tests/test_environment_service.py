"""
Tests for EnvironmentService CRUD operations and validation.
Tests service layer functionality, encryption, validation, and business logic.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from services.environment_service import EnvironmentService
from sqlalchemy_models import EnvironmentVariable, EnvironmentChangeLog


class TestEnvironmentService:
    """Test cases for EnvironmentService"""

    @pytest.fixture
    def service(self, app):
        """Create EnvironmentService instance for testing"""
        with app.app_context():
            return EnvironmentService()

    def test_service_initialization(self, service):
        """Test service initialization and configuration"""
        assert service is not None
        assert hasattr(service, 'logger')
        assert hasattr(service, '_sensitive_patterns')
        assert hasattr(service, '_required_variables')
        assert len(service._sensitive_patterns) > 0
        assert len(service._required_variables) > 0

    def test_is_sensitive_key_detection(self, service):
        """Test automatic detection of sensitive keys"""
        # Test sensitive patterns
        sensitive_keys = [
            'PASSWORD', 'SECRET_KEY', 'API_KEY', 'TOKEN', 'AUTH_TOKEN',
            'JWT_SECRET', 'OAUTH_CLIENT_SECRET', 'SESSION_SECRET',
            'PRIVATE_KEY', 'CREDENTIAL', 'HASH_SALT'
        ]
        
        for key in sensitive_keys:
            assert service._is_sensitive_key(key), f"Key '{key}' should be detected as sensitive"
        
        # Test non-sensitive patterns
        non_sensitive_keys = [
            'DATABASE_URL', 'PORT', 'HOST', 'DEBUG', 'ENVIRONMENT',
            'LOG_LEVEL', 'TIMEOUT', 'MAX_CONNECTIONS'
        ]
        
        for key in non_sensitive_keys:
            assert not service._is_sensitive_key(key), f"Key '{key}' should not be detected as sensitive"

    def test_validate_key_format(self, service):
        """Test key format validation"""
        # Valid keys
        valid_keys = [
            'VALID_KEY', 'TEST_123', 'A', '_UNDERSCORE_START',
            'MIX3D_K3Y', 'LONG_VARIABLE_NAME_WITH_NUMBERS_123'
        ]
        
        for key in valid_keys:
            assert service._validate_key_format(key), f"Key '{key}' should be valid"
        
        # Invalid keys
        invalid_keys = [
            '123_STARTS_WITH_NUMBER', 'INVALID-DASH', 'INVALID SPACE',
            'INVALID.DOT', 'INVALID@SYMBOL', ''
        ]
        
        for key in invalid_keys:
            assert not service._validate_key_format(key), f"Key '{key}' should be invalid"

    def test_validate_key_naming_conventions(self, service):
        """Test comprehensive key naming validation"""
        # Valid keys
        valid, message = service._validate_key_naming_conventions('VALID_KEY')
        assert valid is True
        assert message == "Valid key format"
        
        # Empty key
        valid, message = service._validate_key_naming_conventions('')
        assert valid is False
        assert "cannot be empty" in message
        
        # Too long key
        long_key = 'A' * 256
        valid, message = service._validate_key_naming_conventions(long_key)
        assert valid is False
        assert "cannot exceed 255 characters" in message
        
        # Invalid start character
        valid, message = service._validate_key_naming_conventions('123_INVALID')
        assert valid is False
        assert "must start with a letter or underscore" in message
        
        # Reserved prefix
        valid, message = service._validate_key_naming_conventions('SYSTEM_RESERVED')
        assert valid is False
        assert "reserved prefix" in message

    def test_validate_value_constraints(self, service):
        """Test value validation constraints"""
        # Valid values
        valid, message = service._validate_value_constraints('TEST_KEY', 'valid_value')
        assert valid is True
        assert message == "Valid value"
        
        # None value
        valid, message = service._validate_value_constraints('TEST_KEY', None)
        assert valid is False
        assert "cannot be None" in message
        
        # Too long value
        long_value = 'A' * 10001
        valid, message = service._validate_value_constraints('TEST_KEY', long_value)
        assert valid is False
        assert "cannot exceed 10,000 characters" in message
        
        # URL validation
        valid, message = service._validate_value_constraints('DATABASE_URL', 'invalid_url')
        assert valid is False
        assert "valid protocol" in message
        
        valid, message = service._validate_value_constraints('DATABASE_URL', 'postgresql://localhost:5432/db')
        assert valid is True
        
        # Port validation
        valid, message = service._validate_value_constraints('SERVER_PORT', '99999')
        assert valid is False
        assert "between 1 and 65535" in message
        
        valid, message = service._validate_value_constraints('SERVER_PORT', '8080')
        assert valid is True
        
        # Email validation
        valid, message = service._validate_value_constraints('ADMIN_EMAIL', 'invalid_email')
        assert valid is False
        assert "valid email format" in message
        
        valid, message = service._validate_value_constraints('ADMIN_EMAIL', 'admin@example.com')
        assert valid is True

    def test_get_security_warnings(self, service):
        """Test security warning detection"""
        # Sensitive data in non-sensitive key
        warnings = service._get_security_warnings('PUBLIC_VAR', 'password123')
        assert len(warnings) > 0
        assert any('sensitive data' in warning for warning in warnings)
        
        # Weak sensitive value
        warnings = service._get_security_warnings('SECRET_KEY', '123')
        assert len(warnings) > 0
        assert any('at least 8 characters' in warning for warning in warnings)
        
        # Common weak values
        warnings = service._get_security_warnings('PASSWORD', 'password')
        assert len(warnings) > 0
        assert any('weak password' in warning for warning in warnings)
        
        # No warnings for good values
        warnings = service._get_security_warnings('API_KEY', 'strong_secret_key_12345')
        assert len(warnings) == 0

    @patch('services.environment_service.os.environ', {})
    def test_create_variable_success(self, service, db_setup):
        """Test successful variable creation"""
        result = service.create_variable(
            key='TEST_CREATE',
            value='test_value',
            description='Test description',
            is_required=True,
            created_by='test_user'
        )
        
        assert result['key'] == 'TEST_CREATE'
        assert result['value'] == 'test_value'
        assert result['description'] == 'Test description'
        assert result['is_required'] is True
        assert result['created_by'] == 'test_user'
        
        # Verify in database
        variable = EnvironmentVariable.query.filter_by(key='TEST_CREATE').first()
        assert variable is not None
        assert variable.value == 'test_value'

    def test_create_variable_duplicate_key(self, service, db_setup):
        """Test creating variable with duplicate key"""
        # Create first variable
        service.create_variable(key='DUPLICATE', value='value1')
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            service.create_variable(key='DUPLICATE', value='value2')

    def test_create_variable_invalid_key(self, service, db_setup):
        """Test creating variable with invalid key"""
        with pytest.raises(ValueError, match="Invalid key"):
            service.create_variable(key='123_INVALID', value='test_value')

    def test_create_variable_invalid_value(self, service, db_setup):
        """Test creating variable with invalid value"""
        with pytest.raises(ValueError, match="Invalid value"):
            service.create_variable(key='TEST_KEY', value=None)

    @patch('services.environment_service.os.environ', {})
    def test_create_sensitive_variable_encryption(self, service, db_setup):
        """Test that sensitive variables are encrypted"""
        result = service.create_variable(
            key='SECRET_PASSWORD',
            value='my_secret_password'
        )
        
        # Result should be masked
        assert result['value'] == '********'
        assert result['is_sensitive'] is True
        
        # Database should contain encrypted value
        variable = EnvironmentVariable.query.filter_by(key='SECRET_PASSWORD').first()
        assert variable.value != 'my_secret_password'  # Should be encrypted
        assert len(variable.value) > len('my_secret_password')  # Encrypted is longer

    def test_get_all_variables(self, service, db_setup):
        """Test retrieving all variables"""
        # Create test variables
        service.create_variable(key='PUBLIC_VAR', value='public_value')
        service.create_variable(key='SECRET_VAR', value='secret_value')  # Will be detected as sensitive
        
        # Get all with masking
        variables = service.get_all_variables(mask_sensitive=True)
        assert len(variables) == 2
        
        public_var = next(v for v in variables if v['key'] == 'PUBLIC_VAR')
        secret_var = next(v for v in variables if v['key'] == 'SECRET_VAR')
        
        assert public_var['value'] == 'public_value'
        assert secret_var['value'] == '********'  # Should be masked
        
        # Get all without masking
        variables = service.get_all_variables(mask_sensitive=False)
        secret_var = next(v for v in variables if v['key'] == 'SECRET_VAR')
        assert secret_var['value'] == 'secret_value'  # Should be decrypted

    def test_get_variable(self, service, db_setup):
        """Test retrieving specific variable"""
        service.create_variable(key='GET_TEST', value='test_value')
        
        # Test getting existing variable
        result = service.get_variable('GET_TEST')
        assert result is not None
        assert result['key'] == 'GET_TEST'
        assert result['value'] == 'test_value'
        
        # Test getting non-existent variable
        result = service.get_variable('NON_EXISTENT')
        assert result is None

    def test_get_variable_decrypt_sensitive(self, service, db_setup):
        """Test retrieving sensitive variable with decryption"""
        service.create_variable(key='SECRET_GET', value='secret_value')
        
        # Get without decryption (default)
        result = service.get_variable('SECRET_GET')
        assert result['value'] == '********'
        
        # Get with decryption
        result = service.get_variable('SECRET_GET', decrypt=True)
        assert result['value'] == 'secret_value'

    def test_update_variable_success(self, service, db_setup):
        """Test successful variable update"""
        # Create variable
        service.create_variable(key='UPDATE_TEST', value='original_value')
        
        # Update variable
        result = service.update_variable(
            key='UPDATE_TEST',
            value='updated_value',
            description='Updated description',
            is_required=True,
            updated_by='admin'
        )
        
        assert result['key'] == 'UPDATE_TEST'
        assert result['value'] == 'updated_value'
        assert result['description'] == 'Updated description'
        assert result['is_required'] is True
        
        # Verify in database
        variable = EnvironmentVariable.query.filter_by(key='UPDATE_TEST').first()
        assert variable.value == 'updated_value'
        assert variable.description == 'Updated description'

    def test_update_variable_not_found(self, service, db_setup):
        """Test updating non-existent variable"""
        with pytest.raises(ValueError, match="not found"):
            service.update_variable(key='NON_EXISTENT', value='new_value')

    def test_update_variable_invalid_value(self, service, db_setup):
        """Test updating variable with invalid value"""
        service.create_variable(key='UPDATE_INVALID', value='original')
        
        with pytest.raises(ValueError, match="Invalid value"):
            service.update_variable(key='UPDATE_INVALID', value=None)

    def test_delete_variable_success(self, service, db_setup):
        """Test successful variable deletion"""
        # Create variable
        service.create_variable(key='DELETE_TEST', value='test_value')
        
        # Verify it exists
        assert service.get_variable('DELETE_TEST') is not None
        
        # Delete variable
        result = service.delete_variable(key='DELETE_TEST', deleted_by='admin')
        assert result is True
        
        # Verify it's gone
        assert service.get_variable('DELETE_TEST') is None

    def test_delete_variable_not_found(self, service, db_setup):
        """Test deleting non-existent variable"""
        with pytest.raises(ValueError, match="not found"):
            service.delete_variable(key='NON_EXISTENT')

    def test_delete_required_variable(self, service, db_setup):
        """Test deleting required variable"""
        # Create required variable
        service.create_variable(key='REQUIRED_VAR', value='test', is_required=True)
        
        with pytest.raises(ValueError, match="Cannot delete required"):
            service.delete_variable(key='REQUIRED_VAR')

    def test_delete_critical_system_variable(self, service, db_setup):
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
        
        with pytest.raises(ValueError, match="critical system variable"):
            service.delete_variable(key='FLASK_SECRET_KEY')

    @patch('services.environment_service.os.environ', {})
    def test_apply_all_to_runtime(self, service, db_setup):
        """Test applying all variables to runtime environment"""
        # Create test variables
        service.create_variable(key='RUNTIME_TEST1', value='value1')
        service.create_variable(key='RUNTIME_TEST2', value='value2')
        
        # Apply to runtime
        applied_count, errors = service.apply_all_to_runtime()
        
        assert applied_count == 2
        assert len(errors) == 0
        assert os.environ.get('RUNTIME_TEST1') == 'value1'
        assert os.environ.get('RUNTIME_TEST2') == 'value2'

    def test_validate_required_variables(self, service, db_setup):
        """Test validation of required variables"""
        # Create required variable
        service.create_variable(key='REQUIRED_TEST', value='test', is_required=True)
        
        # Remove from runtime environment
        os.environ.pop('REQUIRED_TEST', None)
        
        # Validate
        result = service.validate_required_variables()
        
        assert 'REQUIRED_TEST' in result['missing_variables']
        assert len(result['warnings']) > 0

    def test_get_validation_summary(self, service, db_setup):
        """Test comprehensive validation summary"""
        # Create various test variables
        service.create_variable(key='VALID_VAR', value='valid_value')
        service.create_variable(key='REQUIRED_VAR', value='required_value', is_required=True)
        service.create_variable(key='SECRET_VAR', value='secret_value')
        
        summary = service.get_validation_summary()
        
        assert 'total_variables' in summary
        assert 'required_variables' in summary
        assert 'sensitive_variables' in summary
        assert 'security_issues' in summary
        assert 'validation_errors' in summary
        
        assert summary['total_variables'] == 3
        assert summary['required_variables'] == 1
        assert summary['sensitive_variables'] == 1

    def test_get_change_history(self, service, db_setup):
        """Test retrieving change history"""
        # Create and update variable to generate history
        service.create_variable(key='HISTORY_TEST', value='original')
        service.update_variable(key='HISTORY_TEST', value='updated')
        service.delete_variable(key='HISTORY_TEST')
        
        # Get history
        history = service.get_change_history()
        assert len(history) >= 3  # CREATE, UPDATE, DELETE
        
        # Get history for specific variable
        history = service.get_change_history(variable_key='HISTORY_TEST')
        assert len(history) == 3
        
        actions = [entry['action'] for entry in history]
        assert 'CREATE' in actions
        assert 'UPDATE' in actions
        assert 'DELETE' in actions

    def test_change_logging(self, service, db_setup):
        """Test that changes are properly logged"""
        # Create variable
        service.create_variable(key='LOG_TEST', value='original', created_by='user1')
        
        # Check create log
        logs = EnvironmentChangeLog.query.filter_by(variable_key='LOG_TEST').all()
        create_log = next(log for log in logs if log.action == 'CREATE')
        assert create_log.changed_by == 'user1'
        assert create_log.new_value == 'original'
        
        # Update variable
        service.update_variable(key='LOG_TEST', value='updated', updated_by='user2')
        
        # Check update log
        logs = EnvironmentChangeLog.query.filter_by(variable_key='LOG_TEST').all()
        update_log = next(log for log in logs if log.action == 'UPDATE')
        assert update_log.changed_by == 'user2'
        assert update_log.old_value == 'original'
        assert update_log.new_value == 'updated'

    def test_encryption_decryption(self, service, app):
        """Test encryption and decryption of sensitive values"""
        with app.app_context():
            # Test encryption
            original_value = 'super_secret_password'
            encrypted_value = service._encrypt_value(original_value)
            
            assert encrypted_value != original_value
            assert len(encrypted_value) > len(original_value)
            
            # Test decryption
            decrypted_value = service._decrypt_value(encrypted_value)
            assert decrypted_value == original_value

    def test_encryption_error_handling(self, service, app):
        """Test encryption error handling"""
        with app.app_context():
            # Test with invalid encryption (simulate error)
            with patch.object(service, '_get_encryption_key', side_effect=Exception("Key error")):
                with pytest.raises(ValueError, match="Failed to encrypt"):
                    service._encrypt_value('test_value')

    def test_is_critical_system_variable(self, service):
        """Test identification of critical system variables"""
        critical_vars = [
            'FLASK_SECRET_KEY', 'DATABASE_URL', 'FLASK_ENV',
            'SECRET_KEY', 'SQLALCHEMY_DATABASE_URI', 'FLASK_APP'
        ]
        
        for var in critical_vars:
            assert service._is_critical_system_variable(var)
        
        non_critical_vars = ['CUSTOM_VAR', 'API_ENDPOINT', 'LOG_LEVEL']
        
        for var in non_critical_vars:
            assert not service._is_critical_system_variable(var)

    def test_service_error_handling(self, service, db_setup):
        """Test service error handling and rollback"""
        # Test database rollback on error
        with patch.object(service, '_encrypt_value', side_effect=Exception("Encryption failed")):
            with pytest.raises(Exception):
                service.create_variable(key='SECRET_FAIL', value='secret')
        
        # Verify variable was not created due to rollback
        assert service.get_variable('SECRET_FAIL') is None

    @patch('services.environment_service.os.environ', {})
    def test_runtime_environment_integration(self, service, db_setup):
        """Test integration with runtime environment"""
        # Create variable
        service.create_variable(key='RUNTIME_INTEGRATION', value='test_value')
        
        # Should be applied to runtime automatically
        assert os.environ.get('RUNTIME_INTEGRATION') == 'test_value'
        
        # Update variable
        service.update_variable(key='RUNTIME_INTEGRATION', value='updated_value')
        
        # Runtime should be updated
        assert os.environ.get('RUNTIME_INTEGRATION') == 'updated_value'
        
        # Delete variable
        service.delete_variable(key='RUNTIME_INTEGRATION')
        
        # Should be removed from runtime
        assert 'RUNTIME_INTEGRATION' not in os.environ

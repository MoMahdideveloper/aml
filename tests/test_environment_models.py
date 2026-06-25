"""
Tests for EnvironmentVariable and EnvironmentChangeLog models.
Tests model functionality, relationships, validation, and data integrity.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from sqlalchemy_models import EnvironmentVariable, EnvironmentChangeLog


class TestEnvironmentVariable:
    """Test cases for EnvironmentVariable model"""

    def test_create_environment_variable(self, db_setup):
        """Test creating a basic environment variable"""
        variable = EnvironmentVariable(
            key="TEST_VAR",
            value="test_value",
            description="Test variable",
            is_sensitive=False,
            is_required=False,
            created_by="test_user"
        )
        
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        assert variable.id is not None
        assert variable.key == "TEST_VAR"
        assert variable.value == "test_value"
        assert variable.description == "Test variable"
        assert variable.is_sensitive is False
        assert variable.is_required is False
        assert variable.created_by == "test_user"
        assert variable.created_at is not None
        assert variable.updated_at is not None

    def test_environment_variable_unique_key_constraint(self, db_setup):
        """Test that environment variable keys must be unique"""
        # Create first variable
        variable1 = EnvironmentVariable(
            key="DUPLICATE_KEY",
            value="value1"
        )
        db_setup.session.add(variable1)
        db_setup.session.commit()
        
        # Try to create second variable with same key
        variable2 = EnvironmentVariable(
            key="DUPLICATE_KEY",
            value="value2"
        )
        db_setup.session.add(variable2)
        
        with pytest.raises(IntegrityError):
            db_setup.session.commit()

    def test_environment_variable_required_fields(self, db_setup):
        """Test that required fields are enforced"""
        # Test missing key
        with pytest.raises(IntegrityError):
            variable = EnvironmentVariable(value="test_value")
            db_setup.session.add(variable)
            db_setup.session.commit()
        
        db_setup.session.rollback()
        
        # Test missing value
        with pytest.raises(IntegrityError):
            variable = EnvironmentVariable(key="TEST_KEY")
            db_setup.session.add(variable)
            db_setup.session.commit()

    def test_environment_variable_defaults(self, db_setup):
        """Test default values for optional fields"""
        variable = EnvironmentVariable(
            key="DEFAULT_TEST",
            value="test_value"
        )
        
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        assert variable.description is None
        assert variable.is_sensitive is False
        assert variable.is_required is False
        assert variable.created_by is None
        assert variable.created_at is not None
        assert variable.updated_at is not None

    def test_environment_variable_updated_at_auto_update(self, db_setup):
        """Test that updated_at is automatically updated on changes"""
        variable = EnvironmentVariable(
            key="UPDATE_TEST",
            value="original_value"
        )
        
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        original_updated_at = variable.updated_at
        
        # Wait a moment and update
        import time
        time.sleep(0.01)
        
        variable.value = "updated_value"
        db_setup.session.commit()
        
        assert variable.updated_at > original_updated_at

    def test_environment_variable_to_dict_with_masking(self, db_setup):
        """Test to_dict method with sensitive value masking"""
        # Test non-sensitive variable
        variable = EnvironmentVariable(
            key="PUBLIC_VAR",
            value="public_value",
            description="Public variable",
            is_sensitive=False,
            is_required=True,
            created_by="admin"
        )
        
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        # Test with masking (default)
        result = variable.to_dict()
        assert result['key'] == "PUBLIC_VAR"
        assert result['value'] == "public_value"
        assert result['is_sensitive'] is False
        
        # Test without masking
        result = variable.to_dict(mask_sensitive=False)
        assert result['value'] == "public_value"

    def test_environment_variable_to_dict_sensitive_masking(self, db_setup):
        """Test to_dict method with sensitive value masking"""
        # Test sensitive variable
        sensitive_variable = EnvironmentVariable(
            key="SECRET_KEY",
            value="super_secret_password",
            is_sensitive=True
        )
        
        db_setup.session.add(sensitive_variable)
        db_setup.session.commit()
        
        # Test with masking (default)
        result = sensitive_variable.to_dict()
        assert result['key'] == "SECRET_KEY"
        assert result['value'] == "********"  # Should be masked
        assert result['is_sensitive'] is True
        
        # Test without masking
        result = sensitive_variable.to_dict(mask_sensitive=False)
        assert result['value'] == "super_secret_password"

    def test_environment_variable_to_dict_empty_sensitive_value(self, db_setup):
        """Test to_dict method with empty sensitive value"""
        variable = EnvironmentVariable(
            key="EMPTY_SECRET",
            value="",
            is_sensitive=True
        )
        
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        result = variable.to_dict()
        assert result['value'] == ""  # Empty string should remain empty

    def test_environment_variable_relationship_with_change_logs(self, db_setup):
        """Test relationship between EnvironmentVariable and EnvironmentChangeLog"""
        variable = EnvironmentVariable(
            key="RELATIONSHIP_TEST",
            value="test_value"
        )
        
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        # Create change log entries
        change_log1 = EnvironmentChangeLog(
            variable_key="RELATIONSHIP_TEST",
            action="CREATE",
            new_value="test_value",
            changed_by="admin",
            environment_variable_id=variable.id
        )
        
        change_log2 = EnvironmentChangeLog(
            variable_key="RELATIONSHIP_TEST",
            action="UPDATE",
            old_value="test_value",
            new_value="updated_value",
            changed_by="admin",
            environment_variable_id=variable.id
        )
        
        db_setup.session.add_all([change_log1, change_log2])
        db_setup.session.commit()
        
        # Test relationship
        assert len(variable.change_logs) == 2
        assert change_log1 in variable.change_logs
        assert change_log2 in variable.change_logs


class TestEnvironmentChangeLog:
    """Test cases for EnvironmentChangeLog model"""

    def test_create_change_log(self, db_setup):
        """Test creating a basic change log entry"""
        change_log = EnvironmentChangeLog(
            variable_key="TEST_VAR",
            action="CREATE",
            old_value=None,
            new_value="test_value",
            changed_by="admin"
        )
        
        db_setup.session.add(change_log)
        db_setup.session.commit()
        
        assert change_log.id is not None
        assert change_log.variable_key == "TEST_VAR"
        assert change_log.action == "CREATE"
        assert change_log.old_value is None
        assert change_log.new_value == "test_value"
        assert change_log.changed_by == "admin"
        assert change_log.changed_at is not None

    def test_change_log_required_fields(self, db_setup):
        """Test that required fields are enforced"""
        # Test missing variable_key
        with pytest.raises(IntegrityError):
            change_log = EnvironmentChangeLog(action="CREATE")
            db_setup.session.add(change_log)
            db_setup.session.commit()
        
        db_setup.session.rollback()
        
        # Test missing action
        with pytest.raises(IntegrityError):
            change_log = EnvironmentChangeLog(variable_key="TEST_VAR")
            db_setup.session.add(change_log)
            db_setup.session.commit()

    def test_change_log_defaults(self, db_setup):
        """Test default values for optional fields"""
        change_log = EnvironmentChangeLog(
            variable_key="DEFAULT_TEST",
            action="UPDATE"
        )
        
        db_setup.session.add(change_log)
        db_setup.session.commit()
        
        assert change_log.old_value is None
        assert change_log.new_value is None
        assert change_log.changed_by is None
        assert change_log.changed_at is not None
        assert change_log.environment_variable_id is None

    def test_change_log_to_dict_with_masking(self, db_setup):
        """Test to_dict method with sensitive value masking"""
        # Create environment variable first
        variable = EnvironmentVariable(
            key="SECRET_VAR",
            value="secret_value",
            is_sensitive=True
        )
        
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        # Create change log
        change_log = EnvironmentChangeLog(
            variable_key="SECRET_VAR",
            action="UPDATE",
            old_value="old_secret",
            new_value="new_secret",
            changed_by="admin",
            environment_variable_id=variable.id
        )
        
        db_setup.session.add(change_log)
        db_setup.session.commit()
        
        # Test with masking (default)
        result = change_log.to_dict()
        assert result['variable_key'] == "SECRET_VAR"
        assert result['action'] == "UPDATE"
        assert result['old_value'] == "********"  # Should be masked
        assert result['new_value'] == "********"  # Should be masked
        assert result['changed_by'] == "admin"
        
        # Test without masking
        result = change_log.to_dict(mask_sensitive=False)
        assert result['old_value'] == "old_secret"
        assert result['new_value'] == "new_secret"

    def test_change_log_to_dict_non_sensitive(self, db_setup):
        """Test to_dict method with non-sensitive variable"""
        # Create non-sensitive environment variable
        variable = EnvironmentVariable(
            key="PUBLIC_VAR",
            value="public_value",
            is_sensitive=False
        )
        
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        # Create change log
        change_log = EnvironmentChangeLog(
            variable_key="PUBLIC_VAR",
            action="UPDATE",
            old_value="old_public",
            new_value="new_public",
            changed_by="admin",
            environment_variable_id=variable.id
        )
        
        db_setup.session.add(change_log)
        db_setup.session.commit()
        
        # Test with masking (should not mask non-sensitive)
        result = change_log.to_dict()
        assert result['old_value'] == "old_public"
        assert result['new_value'] == "new_public"

    def test_change_log_to_dict_without_environment_variable(self, db_setup):
        """Test to_dict method when environment variable is deleted"""
        change_log = EnvironmentChangeLog(
            variable_key="DELETED_VAR",
            action="DELETE",
            old_value="deleted_value",
            new_value=None,
            changed_by="admin",
            environment_variable_id=None
        )
        
        db_setup.session.add(change_log)
        db_setup.session.commit()
        
        # Should not mask when no environment variable exists
        result = change_log.to_dict()
        assert result['old_value'] == "deleted_value"
        assert result['new_value'] is None

    def test_change_log_foreign_key_relationship(self, db_setup):
        """Test foreign key relationship with EnvironmentVariable"""
        # Create environment variable
        variable = EnvironmentVariable(
            key="FK_TEST",
            value="test_value"
        )
        
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        # Create change log with foreign key
        change_log = EnvironmentChangeLog(
            variable_key="FK_TEST",
            action="CREATE",
            new_value="test_value",
            environment_variable_id=variable.id
        )
        
        db_setup.session.add(change_log)
        db_setup.session.commit()
        
        # Test relationship
        assert change_log.environment_variable == variable
        assert change_log in variable.change_logs

    def test_change_log_cascade_behavior(self, db_setup):
        """Test cascade behavior when environment variable is deleted"""
        # Create environment variable
        variable = EnvironmentVariable(
            key="CASCADE_TEST",
            value="test_value"
        )
        
        db_setup.session.add(variable)
        db_setup.session.commit()
        
        # Create change log
        change_log = EnvironmentChangeLog(
            variable_key="CASCADE_TEST",
            action="CREATE",
            new_value="test_value",
            environment_variable_id=variable.id
        )
        
        db_setup.session.add(change_log)
        db_setup.session.commit()
        
        change_log_id = change_log.id
        
        # Delete environment variable
        db_setup.session.delete(variable)
        db_setup.session.commit()
        
        # Change log should still exist but with null foreign key
        remaining_log = EnvironmentChangeLog.query.get(change_log_id)
        assert remaining_log is not None
        assert remaining_log.environment_variable_id is None
        assert remaining_log.environment_variable is None

    def test_change_log_action_types(self, db_setup):
        """Test different action types in change logs"""
        actions = ["CREATE", "UPDATE", "DELETE"]
        
        for action in actions:
            change_log = EnvironmentChangeLog(
                variable_key=f"ACTION_TEST_{action}",
                action=action,
                changed_by="admin"
            )
            
            db_setup.session.add(change_log)
        
        db_setup.session.commit()
        
        # Verify all actions were stored correctly
        for action in actions:
            log = EnvironmentChangeLog.query.filter_by(
                variable_key=f"ACTION_TEST_{action}"
            ).first()
            assert log is not None
            assert log.action == action

    def test_change_log_datetime_handling(self, db_setup):
        """Test datetime handling in change logs"""
        # Create change log
        change_log = EnvironmentChangeLog(
            variable_key="DATETIME_TEST",
            action="CREATE",
            changed_by="admin"
        )
        
        db_setup.session.add(change_log)
        db_setup.session.commit()
        
        # Test that changed_at is set automatically
        assert change_log.changed_at is not None
        assert isinstance(change_log.changed_at, datetime)
        
        # Test that it's recent (within last minute)
        now = datetime.utcnow()
        assert (now - change_log.changed_at) < timedelta(minutes=1)
        
        # Test to_dict datetime serialization
        result = change_log.to_dict()
        assert 'changed_at' in result
        assert result['changed_at'] is not None

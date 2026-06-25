"""
Application service for environment variable configuration.
Implements use-cases for managing environment variables with policy authorization.
"""

from typing import Optional, List, Dict, Any, Tuple
from flask import session

from services.environment_service import environment_service
from domain.policies.environment_policy import (
    can_create_environment_variable,
    can_update_environment_variable,
    can_delete_environment_variable,
    can_view_environment_variables,
    get_current_admin_user
)
from application.result import Success, RetryableError, PermanentError


class EnvironmentConfigService:
    """Application service for environment variable configuration use-cases."""

    def __init__(self):
        self.service = environment_service

    def _check_policy(self, policy_func, action: str) -> None:
        """Check authorization policy and raise error if not authorized."""
        if not policy_func():
            current_user = get_current_admin_user()
            raise PermanentError(
                f"Unauthorized to {action} environment variables. "
                f"Current user: {current_user}"
            )

    def get_all_variables(self, mask_sensitive: bool = True) -> List[Dict]:
        """Retrieve all environment variables with optional sensitive value masking."""
        self._check_policy(can_view_environment_variables, "view")
        return self.service.get_all_variables(mask_sensitive=mask_sensitive)

    def get_variable(self, key: str, decrypt: bool = False) -> Optional[Dict]:
        """Get a specific environment variable by key."""
        self._check_policy(can_view_environment_variables, "view")
        return self.service.get_variable(key, decrypt=decrypt)

    def create_variable(
        self,
        key: str,
        value: str,
        description: Optional[str] = None,
        is_required: bool = False,
        created_by: Optional[str] = None
    ) -> Success[Dict] | RetryableError | PermanentError:
        """Create a new environment variable."""
        self._check_policy(can_create_environment_variable, "create")
        try:
            result = self.service.create_variable(
                key=key,
                value=value,
                description=description,
                is_required=is_required,
                created_by=created_by or get_current_admin_user()
            )
            return Success(result)
        except ValueError as e:
            return RetryableError(str(e))
        except Exception as e:
            return PermanentError(str(e))

    def update_variable(
        self,
        key: str,
        value: str,
        description: Optional[str] = None,
        is_required: Optional[bool] = None,
        updated_by: Optional[str] = None
    ) -> Success[Dict] | RetryableError | PermanentError:
        """Update an existing environment variable."""
        self._check_policy(can_update_environment_variable, "update")
        try:
            result = self.service.update_variable(
                key=key,
                value=value,
                description=description,
                is_required=is_required,
                updated_by=updated_by or get_current_admin_user()
            )
            return Success(result)
        except ValueError as e:
            return RetryableError(str(e))
        except Exception as e:
            return PermanentError(str(e))

    def delete_variable(
        self,
        key: str,
        deleted_by: Optional[str] = None
    ) -> Success[bool] | RetryableError | PermanentError:
        """Delete an environment variable."""
        self._check_policy(can_delete_environment_variable, "delete")
        try:
            result = self.service.delete_variable(
                key=key,
                deleted_by=deleted_by or get_current_admin_user()
            )
            return Success(result)
        except ValueError as e:
            return RetryableError(str(e))
        except Exception as e:
            return PermanentError(str(e))

    def apply_all_to_runtime(self) -> Tuple[int, List[str]]:
        """Apply all stored environment variables to runtime os.environ."""
        self._check_policy(can_view_environment_variables, "apply runtime")
        return self.service.apply_all_to_runtime()

    def validate_required_variables(self) -> Dict[str, List[str]]:
        """Validate that all required environment variables are present."""
        self._check_policy(can_view_environment_variables, "validate")
        return self.service.validate_required_variables()

    def get_validation_summary(self) -> Dict:
        """Get comprehensive validation summary for all environment variables."""
        self._check_policy(can_view_environment_variables, "get validation summary")
        return self.service.get_validation_summary()

    def get_change_history(
        self,
        variable_key: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get change history for environment variables."""
        self._check_policy(can_view_environment_variables, "get change history")
        return self.service.get_change_history(variable_key=variable_key, limit=limit)

    # Runtime environment manager delegations
    def rollback_environment_changes(self) -> Dict:
        """Rollback environment changes."""
        self._check_policy(can_view_environment_variables, "rollback")
        from services.environment_service import runtime_environment_manager
        return runtime_environment_manager.rollback_changes()

    def check_environment_health(self) -> Dict:
        """Check environment health status."""
        self._check_policy(can_view_environment_variables, "health check")
        from services.environment_service import runtime_environment_manager
        return runtime_environment_manager._validate_application_health()
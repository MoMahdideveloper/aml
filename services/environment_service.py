"""
Environment Service for managing environment variables through the admin interface.
Provides CRUD operations, encryption for sensitive values, and runtime environment management.
"""

import logging
import os
import re
from base64 import b64decode, b64encode
from cryptography.fernet import Fernet
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from flask import current_app
from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from database import db
from sqlalchemy_models import EnvironmentChangeLog, EnvironmentVariable
from utils.execution_tracer import log_execution


class EnvironmentService:
    """Service class for managing environment variables"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._sensitive_patterns = [
            r'.*password.*', r'.*secret.*', r'.*key.*', r'.*token.*',
            r'.*api.*key.*', r'.*auth.*', r'.*credential.*', r'.*private.*',
            r'.*jwt.*', r'.*oauth.*', r'.*session.*', r'.*hash.*',
            r'.*salt.*', r'.*cert.*', r'.*ssl.*', r'.*tls.*'
        ]
        self._required_variables = [
            "SESSION_SECRET", "DATABASE_URL", "FLASK_ENV"
        ]
        self._protected_infra_keys = {
            "SESSION_SECRET",
            "FLASK_SECRET_KEY",
            "SECRET_KEY",
            "DATABASE_URL",
            "SQLALCHEMY_DATABASE_URI",
            "FLASK_APP",
            "FLASK_ENV",
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
            "OPENAI_API_KEY",
            "REDIS_URL",
            "CELERY_BROKER_URL",
            "CELERY_RESULT_BACKEND",
            "CACHE_REDIS_URL",
            "RATELIMIT_STORAGE_URI",
            "AUTH_DEFAULT_DENY_ENABLED",
            "ENABLE_CSRF",
            "ADMIN_PASSWORD",
        }
        self._allowlist = self._load_allowlist()

    @log_execution
    def _load_allowlist(self) -> set[str]:
        raw = os.environ.get("ENV_DB_MANAGED_ALLOWLIST", "")
        return {item.strip().upper() for item in raw.split(",") if item.strip()}

    @log_execution
    def _is_protected_key(self, key: str) -> bool:
        normalized = (key or "").strip().upper()
        if normalized in self._protected_infra_keys:
            return True
        if normalized.endswith("_API_KEY"):
            return True
        return False

    @log_execution
    def _is_db_managed_key_allowed(self, key: str) -> Tuple[bool, str]:
        self._allowlist = self._load_allowlist()
        normalized = (key or "").strip().upper()
        if self._is_protected_key(normalized):
            return (
                False,
                f"'{normalized}' is a critical system variable/protected key and must come from process environment/.env",
            )

        if self._allowlist and normalized not in self._allowlist:
            return (
                False,
                f"'{normalized}' is not in ENV_DB_MANAGED_ALLOWLIST and cannot be DB-managed",
            )

        return True, "allowed"

    @log_execution
    def _get_encryption_key(self) -> bytes:
        """Generate encryption key from Flask secret key"""
        secret_key = current_app.secret_key.encode()
        # Pad or truncate to 32 bytes for Fernet
        key = secret_key[:32].ljust(32, b'0')
        return b64encode(key)

    @log_execution
    def _encrypt_value(self, value: str) -> str:
        """Encrypt sensitive values using Flask secret key"""
        try:
            fernet = Fernet(self._get_encryption_key())
            encrypted_bytes = fernet.encrypt(value.encode())
            return b64encode(encrypted_bytes).decode()
        except Exception as e:
            self.logger.error(f"Failed to encrypt value: {e}")
            raise ValueError("Failed to encrypt sensitive value")

    @log_execution
    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt sensitive values"""
        try:
            fernet = Fernet(self._get_encryption_key())
            encrypted_bytes = b64decode(encrypted_value.encode())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            self.logger.error(f"Failed to decrypt value: {e}")
            raise ValueError("Failed to decrypt sensitive value")

    @log_execution
    def _is_sensitive_key(self, key: str) -> bool:
        """Determine if a key contains sensitive data based on patterns"""
        key_lower = key.lower()
        return any(re.match(pattern, key_lower, re.IGNORECASE) for pattern in self._sensitive_patterns)

    @log_execution
    def _validate_key_format(self, key: str) -> bool:
        """Validate environment variable key format"""
        # Allow alphanumeric characters and underscores, must start with letter or underscore
        pattern = r'^[A-Za-z_][A-Za-z0-9_]*$'
        return bool(re.match(pattern, key))
    
    @log_execution
    def _validate_key_naming_conventions(self, key: str) -> Tuple[bool, str]:
        """Validate environment variable key naming conventions with detailed feedback"""
        if not key:
            return False, "Key cannot be empty"
        
        if len(key) > 255:
            return False, "Key cannot exceed 255 characters"
        
        if not re.match(r'^[A-Za-z_]', key):
            return False, "Key must start with a letter or underscore"
        
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
            return False, "Key can only contain letters, numbers, and underscores"
        
        # Check for reserved system variables
        reserved_prefixes = ['SYSTEM_', 'FLASK_', 'PYTHON_', 'PATH', 'HOME', 'USER']
        if any(key.startswith(prefix) for prefix in reserved_prefixes):
            return False, f"Key cannot start with reserved prefix: {', '.join(reserved_prefixes)}"
        
        return True, "Valid key format"
    
    @log_execution
    def _validate_value_constraints(self, key: str, value: str) -> Tuple[bool, str]:
        """Validate environment variable value constraints"""
        if value is None:
            return False, "Value cannot be None"
        
        if len(value) > 10000:  # Reasonable limit for environment variables
            return False, "Value cannot exceed 10,000 characters"
        
        # Specific validation for known variable types
        if key.endswith('_URL') and value:
            # Basic URL validation
            if not (value.startswith('http://') or value.startswith('https://') or 
                   value.startswith('postgresql://') or value.startswith('sqlite://')):
                return False, "URL values should start with a valid protocol (http://, https://, postgresql://, sqlite://)"
        
        if key.endswith('_PORT') and value:
            try:
                port = int(value)
                if not (1 <= port <= 65535):
                    return False, "Port values must be between 1 and 65535"
            except ValueError:
                return False, "Port values must be numeric"
        
        if key.endswith('_EMAIL') and value:
            # Basic email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                return False, "Email values must be in valid email format"
        
        return True, "Valid value"
    
    @log_execution
    def _is_critical_system_variable(self, key: str) -> bool:
        """Check if a variable is critical for system operation"""
        critical_variables = [
            "SESSION_SECRET",
            "FLASK_SECRET_KEY",  # Backward compatibility
            "DATABASE_URL",
            "FLASK_ENV",
            "SECRET_KEY",
            "SQLALCHEMY_DATABASE_URI",
            "FLASK_APP",
        ]
        return key in critical_variables
    
    @log_execution
    def _get_security_warnings(self, key: str, value: str) -> List[str]:
        """Get security warnings for environment variable"""
        warnings = []
        
        # Check for sensitive data in non-sensitive keys
        if not self._is_sensitive_key(key):
            sensitive_patterns = [r'password', r'secret', r'key', r'token', r'auth']
            for pattern in sensitive_patterns:
                if re.search(pattern, value.lower()):
                    warnings.append(f"Value appears to contain sensitive data but key '{key}' is not marked as sensitive")
        
        # Check for weak passwords/secrets
        if self._is_sensitive_key(key) and len(value) < 8:
            warnings.append("Sensitive values should be at least 8 characters long")
        
        # Check for common weak values
        weak_values = ['password', '123456', 'admin', 'secret', 'test', 'default']
        if value.lower() in weak_values:
            warnings.append("Value appears to be a common weak password or default value")
        
        return warnings

    @log_execution
    def _log_change(self, variable_key: str, action: str, old_value: Optional[str] = None, 
                   new_value: Optional[str] = None, changed_by: Optional[str] = None):
        """Log environment variable changes for audit trail"""
        try:
            # Get the environment variable ID for foreign key relationship
            environment_variable_id = None
            if action != "DELETE":  # For DELETE, the variable might already be gone
                variable = EnvironmentVariable.query.filter_by(key=variable_key).first()
                if variable:
                    environment_variable_id = variable.id
            
            change_log = EnvironmentChangeLog(
                variable_key=variable_key,
                action=action,
                old_value=old_value,
                new_value=new_value,
                changed_by=changed_by or "system",
                environment_variable_id=environment_variable_id
            )
            db.session.add(change_log)
            db.session.commit()
        except Exception as e:
            self.logger.error(f"Failed to log change for {variable_key}: {e}")

    @log_execution
    def get_all_variables(self, mask_sensitive: bool = True) -> List[Dict]:
        """Retrieve all environment variables with optional sensitive value masking"""
        try:
            variables = EnvironmentVariable.query.order_by(EnvironmentVariable.key).all()
            result = []
            
            for var in variables:
                var_dict = var.to_dict(mask_sensitive=mask_sensitive)
                # If not masking and value is encrypted, decrypt it
                if not mask_sensitive and var.is_sensitive:
                    try:
                        var_dict['value'] = self._decrypt_value(var.value)
                    except ValueError:
                        # If decryption fails, keep original value
                        var_dict['value'] = var.value
                result.append(var_dict)
            
            return result
        except Exception as e:
            self.logger.error(f"Failed to retrieve environment variables: {e}")
            raise

    @log_execution
    def is_db_managed_key_allowed(self, key: str) -> bool:
        """Public policy helper for callers outside this service."""
        allowed, _ = self._is_db_managed_key_allowed(key)
        return allowed

    @log_execution
    def get_variable(self, key: str, decrypt: bool = False) -> Optional[Dict]:
        """Get a specific environment variable by key"""
        try:
            variable = EnvironmentVariable.query.filter_by(key=key).first()
            if not variable:
                return None
            
            var_dict = variable.to_dict(mask_sensitive=not decrypt)
            
            # Decrypt if requested and variable is sensitive
            if decrypt and variable.is_sensitive:
                try:
                    var_dict['value'] = self._decrypt_value(variable.value)
                except ValueError:
                    var_dict['value'] = variable.value
            
            return var_dict
        except Exception as e:
            self.logger.error(f"Failed to retrieve variable {key}: {e}")
            raise

    @log_execution
    def create_variable(self, key: str, value: str, description: Optional[str] = None,
                       is_required: bool = False, created_by: Optional[str] = None) -> Dict:
        """Create a new environment variable with enhanced validation"""
        try:
            allowed, policy_message = self._is_db_managed_key_allowed(key)
            if not allowed:
                raise ValueError(f"Environment policy violation: {policy_message}")

            # Enhanced key validation
            key_valid, key_message = self._validate_key_naming_conventions(key)
            if not key_valid:
                raise ValueError(f"Invalid key: {key_message}")
            
            # Enhanced value validation
            value_valid, value_message = self._validate_value_constraints(key, value)
            if not value_valid:
                raise ValueError(f"Invalid value: {value_message}")
            
            # Check if key already exists
            existing = EnvironmentVariable.query.filter_by(key=key).first()
            if existing:
                raise ValueError(f"Environment variable '{key}' already exists")
            
            # Get security warnings
            warnings = self._get_security_warnings(key, value)
            if warnings:
                self.logger.warning(f"Security warnings for {key}: {'; '.join(warnings)}")
            
            # Determine if sensitive and encrypt if needed
            is_sensitive = self._is_sensitive_key(key)
            stored_value = value
            if is_sensitive:
                stored_value = self._encrypt_value(value)
            
            # Create new variable
            variable = EnvironmentVariable(
                key=key,
                value=stored_value,
                description=description,
                is_sensitive=is_sensitive,
                is_required=is_required,
                created_by=created_by or "system"
            )
            
            db.session.add(variable)
            db.session.commit()
            
            # Log the change
            self._log_change(key, "CREATE", None, value if not is_sensitive else "***", created_by)
            
            # Apply to runtime environment
            self._apply_single_variable_to_runtime(key, value)
            
            result = variable.to_dict(mask_sensitive=True)
            if warnings:
                result['security_warnings'] = warnings
            
            return result
            
        except IntegrityError:
            db.session.rollback()
            raise ValueError(f"Environment variable '{key}' already exists")
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to create variable {key}: {e}")
            raise

    @log_execution
    def update_variable(self, key: str, value: str, description: Optional[str] = None,
                       is_required: Optional[bool] = None, updated_by: Optional[str] = None) -> Dict:
        """Update an existing environment variable with enhanced validation"""
        try:
            allowed, policy_message = self._is_db_managed_key_allowed(key)
            if not allowed:
                raise ValueError(f"Environment policy violation: {policy_message}")

            variable = EnvironmentVariable.query.filter_by(key=key).first()
            if not variable:
                raise ValueError(f"Environment variable '{key}' not found")
            
            # Enhanced value validation
            value_valid, value_message = self._validate_value_constraints(key, value)
            if not value_valid:
                raise ValueError(f"Invalid value: {value_message}")
            
            # Check if trying to make critical variable non-required
            if is_required is False and self._is_critical_system_variable(key):
                raise ValueError(f"Cannot make critical system variable '{key}' non-required")
            
            # Get security warnings
            warnings = self._get_security_warnings(key, value)
            if warnings:
                self.logger.warning(f"Security warnings for {key}: {'; '.join(warnings)}")
            
            # Get old value for logging (decrypt if sensitive)
            old_value = variable.value
            if variable.is_sensitive:
                try:
                    old_value = self._decrypt_value(variable.value)
                except ValueError:
                    old_value = "***"
            
            # Update fields
            if variable.is_sensitive:
                variable.value = self._encrypt_value(value)
            else:
                variable.value = value
            
            if description is not None:
                variable.description = description
            if is_required is not None:
                variable.is_required = is_required
            
            variable.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log the change
            log_old = old_value if not variable.is_sensitive else "***"
            log_new = value if not variable.is_sensitive else "***"
            self._log_change(key, "UPDATE", log_old, log_new, updated_by)
            
            # Apply to runtime environment
            self._apply_single_variable_to_runtime(key, value)
            
            result = variable.to_dict(mask_sensitive=True)
            if warnings:
                result['security_warnings'] = warnings
            
            return result
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to update variable {key}: {e}")
            raise

    @log_execution
    def delete_variable(self, key: str, deleted_by: Optional[str] = None) -> bool:
        """Delete an environment variable with enhanced validation"""
        try:
            allowed, policy_message = self._is_db_managed_key_allowed(key)
            if not allowed:
                raise ValueError(f"Environment policy violation: {policy_message}")

            variable = EnvironmentVariable.query.filter_by(key=key).first()
            if not variable:
                raise ValueError(f"Environment variable '{key}' not found")
            
            # Check if required variable
            if variable.is_required:
                raise ValueError(f"Cannot delete required environment variable '{key}'. Mark as non-required first.")
            
            # Check if critical system variable
            if self._is_critical_system_variable(key):
                raise ValueError(f"Cannot delete critical system variable '{key}'. This may break the application.")
            
            # Get old value and ID for logging before deletion
            old_value = variable.value
            variable_id = variable.id
            if variable.is_sensitive:
                try:
                    old_value = self._decrypt_value(variable.value)
                except ValueError:
                    old_value = "***"
            
            # Log the change before deletion (with variable ID)
            log_old = old_value if not variable.is_sensitive else "***"
            change_log = EnvironmentChangeLog(
                variable_key=key,
                action="DELETE",
                old_value=log_old,
                new_value=None,
                changed_by=deleted_by or "system",
                environment_variable_id=variable_id
            )
            db.session.add(change_log)
            
            # Delete the variable
            db.session.delete(variable)
            db.session.commit()
            
            # Remove from runtime environment
            self._remove_from_runtime(key)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Failed to delete variable {key}: {e}")
            raise

    @log_execution
    def _apply_single_variable_to_runtime(self, key: str, value: str) -> Dict[str, any]:
        """Apply a single environment variable to runtime os.environ with comprehensive error handling"""
        try:
            allowed, policy_message = self._is_db_managed_key_allowed(key)
            if not allowed:
                return {
                    "success": False,
                    "message": f"Skipped protected/runtime-managed key: {policy_message}",
                }

            # Use the enhanced RuntimeEnvironmentManager for better error handling
            result = runtime_environment_manager.update_environment(key, value)
            
            if result['success']:
                self.logger.info(f"Applied environment variable {key} to runtime")
                return result
            else:
                self.logger.error(f"Failed to apply variable {key} to runtime: {result['message']}")
                raise RuntimeError(result['message'])
                
        except Exception as e:
            self.logger.error(f"Failed to apply variable {key} to runtime: {e}")
            raise

    @log_execution
    def _remove_from_runtime(self, key: str) -> Dict[str, any]:
        """Remove an environment variable from runtime os.environ with comprehensive error handling"""
        try:
            allowed, policy_message = self._is_db_managed_key_allowed(key)
            if not allowed:
                return {
                    "success": False,
                    "message": f"Skipped protected/runtime-managed key removal: {policy_message}",
                }

            # Use the enhanced RuntimeEnvironmentManager for better error handling
            result = runtime_environment_manager.remove_from_environment(key)
            
            if result['success']:
                self.logger.info(f"Removed environment variable {key} from runtime")
                return result
            else:
                self.logger.error(f"Failed to remove variable {key} from runtime: {result['message']}")
                raise RuntimeError(result['message'])
                
        except Exception as e:
            self.logger.error(f"Failed to remove variable {key} from runtime: {e}")
            raise

    @log_execution
    def apply_all_to_runtime(self) -> Tuple[int, List[str]]:
        """Apply all stored environment variables to runtime os.environ"""
        applied_count = 0
        errors = []

        try:
            variables = EnvironmentVariable.query.all()

            for variable in variables:
                try:
                    allowed, policy_message = self._is_db_managed_key_allowed(variable.key)
                    if not allowed:
                        warning = f"Skipped {variable.key}: {policy_message}"
                        errors.append(warning)
                        self.logger.warning(warning)
                        continue

                    value = variable.value
                    if variable.is_sensitive:
                        value = self._decrypt_value(variable.value)
                    
                    os.environ[variable.key] = value
                    applied_count += 1
                    
                except Exception as e:
                    error_msg = f"Failed to apply {variable.key}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            self.logger.info(f"Applied {applied_count} environment variables to runtime")
            return applied_count, errors
            
        except Exception as e:
            self.logger.error(f"Failed to apply environment variables to runtime: {e}")
            raise

    @log_execution
    def validate_required_variables(self) -> Dict[str, List[str]]:
        """Validate that all required environment variables are present and provide warnings"""
        try:
            required_vars = EnvironmentVariable.query.filter_by(is_required=True).all()
            missing_vars = []
            warnings = []
            
            for var in required_vars:
                if var.key not in os.environ:
                    missing_vars.append(var.key)
                    if self._is_critical_system_variable(var.key):
                        warnings.append(f"Critical system variable '{var.key}' is missing - application may not function properly")
                    else:
                        warnings.append(f"Required variable '{var.key}' is missing")
            
            # Check for critical system variables that should be required.
            required_keys = [var.key for var in required_vars]
            for critical_var in ["SESSION_SECRET", "DATABASE_URL"]:
                # SESSION_SECRET can be temporarily satisfied by FLASK_SECRET_KEY.
                if critical_var == "SESSION_SECRET":
                    if "SESSION_SECRET" not in required_keys and "FLASK_SECRET_KEY" not in required_keys:
                        warnings.append("Critical variable 'SESSION_SECRET' should be marked as required")
                elif critical_var not in required_keys:
                    warnings.append(f"Critical variable '{critical_var}' should be marked as required")
            
            return {
                'missing_variables': missing_vars,
                'warnings': warnings
            }
            
        except Exception as e:
            self.logger.error(f"Failed to validate required variables: {e}")
            raise
    
    @log_execution
    def get_validation_summary(self) -> Dict:
        """Get comprehensive validation summary for all environment variables"""
        try:
            validation_result = self.validate_required_variables()
            all_vars = EnvironmentVariable.query.all()
            
            security_issues = []
            validation_errors = []
            blocked_variables = []

            for var in all_vars:
                allowed, policy_message = self._is_db_managed_key_allowed(var.key)
                if not allowed:
                    blocked_variables.append(f"{var.key}: {policy_message}")

                # Check key naming conventions
                key_valid, key_message = self._validate_key_naming_conventions(var.key)
                if not key_valid:
                    validation_errors.append(f"Variable '{var.key}': {key_message}")
                
                # Get current value for validation (decrypt if needed)
                current_value = var.value
                if var.is_sensitive:
                    try:
                        current_value = self._decrypt_value(var.value)
                    except ValueError:
                        security_issues.append(f"Variable '{var.key}': Failed to decrypt sensitive value")
                        continue
                
                # Check value constraints
                value_valid, value_message = self._validate_value_constraints(var.key, current_value)
                if not value_valid:
                    validation_errors.append(f"Variable '{var.key}': {value_message}")
                
                # Check security warnings
                warnings = self._get_security_warnings(var.key, current_value)
                if warnings:
                    security_issues.extend([f"Variable '{var.key}': {warning}" for warning in warnings])
            
            return {
                'missing_required_variables': validation_result['missing_variables'],
                'requirement_warnings': validation_result['warnings'],
                'security_issues': security_issues,
                'validation_errors': validation_errors,
                'blocked_variables': blocked_variables,
                'blocked_variables_count': len(blocked_variables),
                'total_variables': len(all_vars),
                'required_variables': len([var for var in all_vars if var.is_required]),
                'sensitive_variables': len([var for var in all_vars if var.is_sensitive])
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get validation summary: {e}")
            raise

    @log_execution
    def get_change_history(self, variable_key: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get change history for environment variables"""
        try:
            query = EnvironmentChangeLog.query
            
            if variable_key:
                query = query.filter_by(variable_key=variable_key)
            
            changes = query.order_by(desc(EnvironmentChangeLog.changed_at)).limit(limit).all()
            
            # Return dictionaries with proper datetime handling for templates
            result = []
            for change in changes:
                change_dict = change.to_dict(mask_sensitive=True)
                # Keep the datetime object for template formatting
                change_dict['changed_at'] = change.changed_at
                result.append(change_dict)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve change history: {e}")
            raise


class RuntimeEnvironmentManager:
    """Manager for runtime environment operations with validation and rollback"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._backup_state = {}
        self._change_history = []
        self._max_history = 10

    @log_execution
    def backup_current_state(self):
        """Create backup of current environment state"""
        try:
            self._backup_state = dict(os.environ)
            self.logger.info("Created backup of current environment state")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise RuntimeError(f"Failed to create environment backup: {str(e)}")

    @log_execution
    def update_environment(self, key: str, value: str) -> Dict[str, any]:
        """Update runtime environment with comprehensive validation and rollback"""
        operation_result = {
            'success': False,
            'message': '',
            'warnings': [],
            'rollback_performed': False,
            'health_check_passed': False
        }
        
        try:
            # Validate inputs
            if not key or not isinstance(key, str):
                raise ValueError("Environment variable key must be a non-empty string")
            
            if value is None:
                raise ValueError("Environment variable value cannot be None")
            
            # Store old value for rollback
            old_value = os.environ.get(key)
            
            # Create backup before making changes
            self.backup_current_state()
            
            # Record the change for history
            change_record = {
                'timestamp': datetime.utcnow(),
                'action': 'UPDATE',
                'key': key,
                'old_value': old_value,
                'new_value': value,
                'success': False
            }
            
            # Apply the change
            os.environ[key] = value
            self.logger.info(f"Applied environment variable {key} to runtime")
            
            # Perform comprehensive health check
            health_result = self._validate_application_health()
            operation_result['health_check_passed'] = health_result['success']
            
            if health_result['success']:
                # Success case
                change_record['success'] = True
                operation_result['success'] = True
                operation_result['message'] = f"Successfully updated environment variable '{key}'"
                
                if health_result['warnings']:
                    operation_result['warnings'] = health_result['warnings']
                
                self.logger.info(f"Successfully updated environment variable {key}")
                
            else:
                # Health check failed - perform rollback
                self.logger.warning(f"Health check failed after updating {key}: {health_result['error']}")
                
                try:
                    if old_value is not None:
                        os.environ[key] = old_value
                    else:
                        os.environ.pop(key, None)
                    
                    operation_result['rollback_performed'] = True
                    operation_result['message'] = f"Environment variable '{key}' update failed and was rolled back: {health_result['error']}"
                    
                    self.logger.info(f"Successfully rolled back environment variable {key}")
                    
                except Exception as rollback_error:
                    self.logger.error(f"Failed to rollback {key}: {rollback_error}")
                    operation_result['message'] += f" Additionally, rollback failed: {str(rollback_error)}"
                
                raise ValueError(f"Application health check failed: {health_result['error']}")
            
        except Exception as e:
            change_record['success'] = False
            change_record['error'] = str(e)
            operation_result['message'] = f"Failed to update environment variable '{key}': {str(e)}"
            self.logger.error(f"Failed to update environment variable {key}: {e}")
            raise
        
        finally:
            # Always record the change attempt
            self._add_to_history(change_record)
        
        return operation_result

    @log_execution
    def remove_from_environment(self, key: str) -> Dict[str, any]:
        """Remove variable from runtime environment with comprehensive validation and rollback"""
        operation_result = {
            'success': False,
            'message': '',
            'warnings': [],
            'rollback_performed': False,
            'health_check_passed': False
        }
        
        try:
            # Validate input
            if not key or not isinstance(key, str):
                raise ValueError("Environment variable key must be a non-empty string")
            
            old_value = os.environ.get(key)
            if old_value is None:
                operation_result['success'] = True
                operation_result['message'] = f"Environment variable '{key}' was already not set"
                return operation_result
            
            # Create backup before making changes
            self.backup_current_state()
            
            # Record the change for history
            change_record = {
                'timestamp': datetime.utcnow(),
                'action': 'DELETE',
                'key': key,
                'old_value': old_value,
                'new_value': None,
                'success': False
            }
            
            # Remove the variable
            del os.environ[key]
            self.logger.info(f"Removed environment variable {key} from runtime")
            
            # Perform comprehensive health check
            health_result = self._validate_application_health()
            operation_result['health_check_passed'] = health_result['success']
            
            if health_result['success']:
                # Success case
                change_record['success'] = True
                operation_result['success'] = True
                operation_result['message'] = f"Successfully removed environment variable '{key}'"
                
                if health_result['warnings']:
                    operation_result['warnings'] = health_result['warnings']
                
                self.logger.info(f"Successfully removed environment variable {key}")
                
            else:
                # Health check failed - perform rollback
                self.logger.warning(f"Health check failed after removing {key}: {health_result['error']}")
                
                try:
                    os.environ[key] = old_value
                    operation_result['rollback_performed'] = True
                    operation_result['message'] = f"Environment variable '{key}' removal failed and was rolled back: {health_result['error']}"
                    
                    self.logger.info(f"Successfully rolled back environment variable {key}")
                    
                except Exception as rollback_error:
                    self.logger.error(f"Failed to rollback {key}: {rollback_error}")
                    operation_result['message'] += f" Additionally, rollback failed: {str(rollback_error)}"
                
                raise ValueError(f"Application health check failed: {health_result['error']}")
            
        except Exception as e:
            change_record['success'] = False
            change_record['error'] = str(e)
            operation_result['message'] = f"Failed to remove environment variable '{key}': {str(e)}"
            self.logger.error(f"Failed to remove environment variable {key}: {e}")
            raise
        
        finally:
            # Always record the change attempt
            self._add_to_history(change_record)
        
        return operation_result

    @log_execution
    def rollback_changes(self) -> Dict[str, any]:
        """Rollback to backed up environment state with comprehensive error handling"""
        operation_result = {
            'success': False,
            'message': '',
            'variables_restored': 0,
            'variables_failed': 0,
            'errors': []
        }
        
        try:
            if not self._backup_state:
                raise ValueError("No backup state available for rollback")
            
            # Record current state for comparison
            current_state = dict(os.environ)
            
            # Clear current environment
            os.environ.clear()
            
            # Restore backup state variable by variable
            restored_count = 0
            failed_count = 0
            errors = []
            
            for key, value in self._backup_state.items():
                try:
                    os.environ[key] = value
                    restored_count += 1
                except Exception as e:
                    failed_count += 1
                    error_msg = f"Failed to restore {key}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            operation_result['variables_restored'] = restored_count
            operation_result['variables_failed'] = failed_count
            operation_result['errors'] = errors
            
            if failed_count == 0:
                operation_result['success'] = True
                operation_result['message'] = f"Successfully rolled back environment changes. Restored {restored_count} variables."
                self.logger.info(f"Successfully rolled back environment changes. Restored {restored_count} variables.")
            else:
                operation_result['message'] = f"Partially rolled back environment changes. Restored {restored_count} variables, failed {failed_count}."
                self.logger.warning(f"Partial rollback: restored {restored_count}, failed {failed_count}")
            
            # Record rollback operation
            change_record = {
                'timestamp': datetime.utcnow(),
                'action': 'ROLLBACK',
                'key': 'ALL_VARIABLES',
                'old_value': f"{len(current_state)} variables",
                'new_value': f"{restored_count} variables restored",
                'success': operation_result['success'],
                'details': f"Restored: {restored_count}, Failed: {failed_count}"
            }
            self._add_to_history(change_record)
            
        except Exception as e:
            operation_result['message'] = f"Failed to rollback environment changes: {str(e)}"
            self.logger.error(f"Failed to rollback environment changes: {e}")
            raise
        
        return operation_result

    @log_execution
    def _validate_application_health(self) -> Dict[str, any]:
        """Comprehensive application health validation after environment changes"""
        health_result = {
            'success': True,
            'error': None,
            'warnings': [],
            'checks_performed': []
        }
        
        try:
            # Check 1: Basic Python imports
            try:
                import flask
                import sqlalchemy
                health_result['checks_performed'].append("Basic imports: PASSED")
            except ImportError as e:
                health_result['success'] = False
                health_result['error'] = f"Critical import failed: {str(e)}"
                return health_result
            
            # Check 2: Database connection
            try:
                from database import db
                if hasattr(db, 'engine'):
                    # Test database connection with a simple query
                    with db.engine.connect() as conn:
                        conn.execute(db.text('SELECT 1'))
                    health_result['checks_performed'].append("Database connection: PASSED")
                else:
                    health_result['warnings'].append("Database engine not available for testing")
            except Exception as e:
                health_result['success'] = False
                health_result['error'] = f"Database connection failed: {str(e)}"
                return health_result
            
            # Check 3: Flask app configuration
            try:
                from flask import current_app
                if current_app:
                    # Check critical Flask configuration
                    if not current_app.secret_key:
                        health_result['warnings'].append("Flask secret key is not set")
                    
                    health_result['checks_performed'].append("Flask configuration: PASSED")
                else:
                    health_result['warnings'].append("Flask app context not available")
            except Exception as e:
                health_result['warnings'].append(f"Flask configuration check failed: {str(e)}")
            
            # Check 4: Critical environment variables
            critical_vars = ["SESSION_SECRET", "DATABASE_URL"]
            missing_critical = []
            for var in critical_vars:
                if var == "SESSION_SECRET":
                    if "SESSION_SECRET" not in os.environ and "FLASK_SECRET_KEY" not in os.environ:
                        missing_critical.append(var)
                elif var not in os.environ:
                    missing_critical.append(var)
            
            if missing_critical:
                health_result['warnings'].append(f"Missing critical environment variables: {', '.join(missing_critical)}")
            else:
                health_result['checks_performed'].append("Critical environment variables: PASSED")
            
            # Check 5: Memory and resource usage (basic check)
            try:
                import psutil
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 90:
                    health_result['warnings'].append(f"High memory usage: {memory_percent}%")
                health_result['checks_performed'].append(f"System resources: Memory {memory_percent}%")
            except ImportError:
                health_result['warnings'].append("psutil not available for resource monitoring")
            except Exception as e:
                health_result['warnings'].append(f"Resource check failed: {str(e)}")
            
        except Exception as e:
            health_result['success'] = False
            health_result['error'] = f"Health validation failed: {str(e)}"
            self.logger.error(f"Health validation error: {e}")
        
        return health_result

    @log_execution
    def _add_to_history(self, change_record: Dict):
        """Add change record to history with size management"""
        try:
            self._change_history.append(change_record)
            
            # Keep only the most recent changes
            if len(self._change_history) > self._max_history:
                self._change_history = self._change_history[-self._max_history:]
                
        except Exception as e:
            self.logger.error(f"Failed to add change to history: {e}")

    @log_execution
    def get_change_history(self) -> List[Dict]:
        """Get recent change history"""
        return list(self._change_history)

    @log_execution
    def clear_history(self):
        """Clear change history"""
        self._change_history.clear()
        self.logger.info("Cleared runtime environment change history")

    @log_execution
    def get_backup_info(self) -> Dict[str, any]:
        """Get information about current backup state"""
        return {
            'has_backup': bool(self._backup_state),
            'backup_size': len(self._backup_state),
            'backup_keys': list(self._backup_state.keys()) if self._backup_state else []
        }


# Global service instances
environment_service = EnvironmentService()
runtime_environment_manager = RuntimeEnvironmentManager()

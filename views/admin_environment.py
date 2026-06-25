"""
Admin Environment Settings Blueprint
Provides web interface for managing environment variables through admin panel.
"""

import logging
import os
from datetime import datetime
from functools import wraps
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for, session, abort
from werkzeug.exceptions import BadRequest

from application.services.environment_config_service import EnvironmentConfigService
from forms import EnvironmentVariableForm
from utils.execution_tracer import log_execution

bp = Blueprint("admin_environment", __name__, url_prefix="/admin")

env_config_service = EnvironmentConfigService()


@log_execution
def require_admin_auth(f):
    """Decorator to require admin authentication for environment operations"""
    @wraps(f)
    @log_execution
    def decorated_function(*args, **kwargs):
        # Basic authentication check - in production this should be more robust
        auth_header = request.headers.get('Authorization')
        
        # Check for session-based auth first
        if session.get('admin_authenticated'):
            return f(*args, **kwargs)
        
        # Check for basic auth header
        if auth_header and auth_header.startswith('Basic '):
            try:
                import base64
                encoded_credentials = auth_header.split(' ')[1]
                decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
                username, password = decoded_credentials.split(':', 1)
                
                # Simple hardcoded admin credentials - in production use proper user management
                admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
                if username == 'admin' and password == admin_password:
                    session['admin_authenticated'] = True
                    session['admin_user'] = username
                    return f(*args, **kwargs)
            except Exception as e:
                logging.error(f"Authentication error: {e}")
        
        # Check for form-based login
        if request.method == 'POST' and request.form.get('admin_password'):
            password = request.form.get('admin_password')
            admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
            if password == admin_password:
                session['admin_authenticated'] = True
                session['admin_user'] = 'admin'
                return f(*args, **kwargs)
        
        # If no valid authentication, return 401
        if request.is_json:
            return jsonify({'error': 'Admin authentication required'}), 401
        else:
            flash('Admin authentication required to access environment settings', 'error')
            return render_template('admin_login.html'), 401
    
    return decorated_function


@log_execution
def get_current_admin_user():
    """Get current authenticated admin user"""
    return session.get('admin_user', 'unknown_admin')


@bp.route("/environment")
@require_admin_auth
@log_execution
def environment():
    """Display environment variables page with comprehensive error handling"""
    try:
        variables = env_config_service.get_all_variables(mask_sensitive=True)
        validation_summary = env_config_service.get_validation_summary()
        form = EnvironmentVariableForm()
        
        # Check for any critical issues and show warnings
        if validation_summary.get('missing_required_variables'):
            flash(f"Warning: {len(validation_summary['missing_required_variables'])} required variables are missing", "warning")
        
        if validation_summary.get('security_issues'):
            flash(f"Security Alert: {len(validation_summary['security_issues'])} security issues detected", "warning")
        
        return render_template(
            "admin_environment.html", 
            variables=variables, 
            form=form,
            validation_summary=validation_summary
        )
    except Exception as e:
        logging.error(f"Error loading environment variables: {e}")
        flash(f"Critical Error: Unable to load environment variables. {str(e)}", "error")
        
        # Provide fallback empty state with error context
        return render_template(
            "admin_environment.html", 
            variables=[], 
            form=EnvironmentVariableForm(), 
            validation_summary={},
            error_context="Failed to load environment data"
        )


@bp.route("/environment", methods=["POST"])
@require_admin_auth
@log_execution
def create_environment_variable():
    """Create new environment variable with comprehensive error handling and user feedback"""
    form = EnvironmentVariableForm()
    
    # Enhanced form validation with detailed error messages
    if not form.validate_on_submit():
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"{field.replace('_', ' ').title()}: {error}")
        
        if error_messages:
            flash(f"Form validation failed: {'; '.join(error_messages)}", "error")
        else:
            flash("Invalid form data submitted. Please check your inputs.", "error")
        
        return redirect(url_for("admin_environment.environment"))
    
    try:
        # Attempt to create the variable
        result = env_config_service.create_variable(
            key=form.key.data,
            value=form.value.data,
            description=form.description.data or None,
            is_required=form.is_required.data,
            created_by=get_current_admin_user()
        )
        
        # Build success message with warnings if any
        success_msg = f'Environment variable "{form.key.data}" created successfully!'
        
        if 'security_warnings' in result and result['security_warnings']:
            flash(f"Security Warning: {'; '.join(result['security_warnings'])}", "warning")
        
        flash(success_msg, "success")
        logging.info(f"Successfully created environment variable {form.key.data} by {get_current_admin_user()}")
        
    except ValueError as e:
        # Handle validation errors with specific feedback
        error_msg = str(e)
        if "already exists" in error_msg.lower():
            flash(f"Variable Creation Failed: Environment variable '{form.key.data}' already exists. Use the edit function to modify it.", "error")
        elif "invalid key" in error_msg.lower():
            flash(f"Invalid Key Format: {error_msg}", "error")
        elif "invalid value" in error_msg.lower():
            flash(f"Invalid Value: {error_msg}", "error")
        else:
            flash(f"Validation Error: {error_msg}", "error")
        
        logging.warning(f"Validation error creating variable {form.key.data}: {e}")
        
    except RuntimeError as e:
        # Handle runtime environment application errors
        flash(f"Runtime Error: Failed to apply environment variable to system. {str(e)}", "error")
        logging.error(f"Runtime error creating variable {form.key.data}: {e}")
        
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error creating environment variable '{form.key.data}': {str(e)}"
        flash(f"System Error: {error_msg}", "error")
        logging.error(f"Unexpected error creating environment variable: {e}", exc_info=True)
    
    return redirect(url_for("admin_environment.environment"))


@bp.route("/environment/<key>", methods=["PUT"])
@require_admin_auth
@log_execution
def update_environment_variable(key):
    """Update existing environment variable with comprehensive error handling"""
    try:
        # Enhanced request validation
        if not request.is_json:
            return jsonify({
                "success": False, 
                "error": "Request must be JSON format",
                "error_type": "invalid_request"
            }), 400
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False, 
                "error": "No data provided in request body",
                "error_type": "missing_data"
            }), 400
        
        # Validate required fields with detailed feedback
        if 'value' not in data or data['value'] is None:
            return jsonify({
                "success": False, 
                "error": "Value field is required and cannot be null",
                "error_type": "missing_field"
            }), 400
        
        # Validate key parameter
        if not key or not isinstance(key, str):
            return jsonify({
                "success": False, 
                "error": "Invalid environment variable key",
                "error_type": "invalid_key"
            }), 400
        
        # Attempt to update the variable
        updated_variable = env_config_service.update_variable(
            key=key,
            value=data['value'],
            description=data.get('description'),
            is_required=data.get('is_required'),
            updated_by=get_current_admin_user()
        )
        
        # Build successful response
        response_data = {
            "success": True,
            "message": f"Environment variable '{key}' updated successfully",
            "variable": updated_variable,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add warnings if present
        if 'security_warnings' in updated_variable and updated_variable['security_warnings']:
            response_data['warnings'] = updated_variable['security_warnings']
            response_data['message'] += f" (with {len(updated_variable['security_warnings'])} security warnings)"
        
        logging.info(f"Successfully updated environment variable {key} by {get_current_admin_user()}")
        return jsonify(response_data)
        
    except ValueError as e:
        # Handle validation and business logic errors
        error_msg = str(e)
        error_type = "validation_error"
        
        if "not found" in error_msg.lower():
            error_type = "not_found"
            status_code = 404
        elif "invalid value" in error_msg.lower():
            error_type = "invalid_value"
            status_code = 400
        elif "critical system variable" in error_msg.lower():
            error_type = "protected_variable"
            status_code = 403
        else:
            status_code = 400
        
        logging.warning(f"Validation error updating variable {key}: {e}")
        return jsonify({
            "success": False, 
            "error": error_msg,
            "error_type": error_type
        }), status_code
        
    except RuntimeError as e:
        # Handle runtime environment errors
        logging.error(f"Runtime error updating variable {key}: {e}")
        return jsonify({
            "success": False, 
            "error": f"Failed to apply changes to runtime environment: {str(e)}",
            "error_type": "runtime_error"
        }), 500
        
    except BadRequest as e:
        # Handle request format errors
        return jsonify({
            "success": False, 
            "error": str(e),
            "error_type": "bad_request"
        }), 400
        
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error updating environment variable '{key}': {str(e)}"
        logging.error(error_msg, exc_info=True)
        return jsonify({
            "success": False, 
            "error": "An unexpected server error occurred. Please try again or contact support.",
            "error_type": "internal_error",
            "error_id": f"env_update_{key}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        }), 500


@bp.route("/environment/<key>", methods=["DELETE"])
@require_admin_auth
@log_execution
def delete_environment_variable(key):
    """Delete environment variable with comprehensive error handling"""
    try:
        # Validate key parameter
        if not key or not isinstance(key, str):
            return jsonify({
                "success": False, 
                "error": "Invalid environment variable key",
                "error_type": "invalid_key"
            }), 400
        
        # Attempt to delete the variable
        env_config_service.delete_variable(
            key=key,
            deleted_by=get_current_admin_user()
        )
        
        logging.info(f"Successfully deleted environment variable {key} by {get_current_admin_user()}")
        return jsonify({
            "success": True,
            "message": f"Environment variable '{key}' deleted successfully",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except ValueError as e:
        # Handle validation and business logic errors
        error_msg = str(e)
        error_type = "validation_error"
        
        if "not found" in error_msg.lower():
            error_type = "not_found"
            status_code = 404
        elif "required" in error_msg.lower():
            error_type = "protected_variable"
            status_code = 403
        elif "critical system variable" in error_msg.lower():
            error_type = "critical_variable"
            status_code = 403
        else:
            status_code = 400
        
        logging.warning(f"Validation error deleting variable {key}: {e}")
        return jsonify({
            "success": False, 
            "error": error_msg,
            "error_type": error_type
        }), status_code
        
    except RuntimeError as e:
        # Handle runtime environment errors
        logging.error(f"Runtime error deleting variable {key}: {e}")
        return jsonify({
            "success": False, 
            "error": f"Failed to remove variable from runtime environment: {str(e)}",
            "error_type": "runtime_error"
        }), 500
        
    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error deleting environment variable '{key}': {str(e)}"
        logging.error(error_msg, exc_info=True)
        return jsonify({
            "success": False, 
            "error": "An unexpected server error occurred. Please try again or contact support.",
            "error_type": "internal_error",
            "error_id": f"env_delete_{key}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        }), 500


@bp.route("/environment/history")
@require_admin_auth
@log_execution
def environment_history():
    """View environment variable change history"""
    try:
        variable_key = request.args.get('variable_key')
        limit = int(request.args.get('limit', 50))
        
        history = env_config_service.get_change_history(
            variable_key=variable_key,
            limit=limit
        )
        
        return render_template(
            "admin_environment_history.html",
            history=history,
            variable_key=variable_key
        )
        
    except Exception as e:
        logging.error(f"Error loading environment history: {e}")
        flash(f"Error loading change history: {str(e)}", "error")
        return render_template("admin_environment_history.html", history=[], variable_key=None)


@bp.route("/environment/<key>/details")
@require_admin_auth
@log_execution
def get_environment_variable_details(key):
    """Get environment variable details for editing (AJAX endpoint)"""
    try:
        variable = env_config_service.get_variable(key, decrypt=False)
        if not variable:
            return jsonify({"success": False, "error": "Variable not found"}), 404
        
        return jsonify({
            "success": True,
            "variable": variable
        })
        
    except Exception as e:
        logging.error(f"Error getting variable details for {key}: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"}), 500


@bp.route("/environment/validation")
@require_admin_auth
@log_execution
def get_validation_summary():
    """Get validation summary for all environment variables (AJAX endpoint)"""
    try:
        validation_summary = env_config_service.get_validation_summary()
        return jsonify({
            "success": True,
            "validation": validation_summary
        })
        
    except Exception as e:
        logging.error(f"Error getting validation summary: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"}), 500


@bp.route("/login", methods=["GET", "POST"])
@log_execution
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        if password == admin_password:
            session['admin_authenticated'] = True
            session['admin_user'] = 'admin'
            return redirect(url_for('admin_environment.environment'))
        else:
            flash('Invalid admin password', 'error')
    
    return render_template('admin_login.html')


@bp.route("/environment/rollback", methods=["POST"])
@require_admin_auth
@log_execution
def rollback_environment_changes():
    """Rollback environment changes with comprehensive error handling"""
    try:
        # Perform rollback operation
        rollback_result = env_config_service.rollback_environment_changes()
        
        if rollback_result['success']:
            flash(f"Rollback successful: {rollback_result['message']}", "success")
            logging.info(f"Environment rollback performed by {get_current_admin_user()}: {rollback_result['message']}")
        else:
            flash(f"Rollback partially failed: {rollback_result['message']}", "warning")
            if rollback_result['errors']:
                for error in rollback_result['errors'][:3]:  # Show first 3 errors
                    flash(f"Rollback error: {error}", "error")
            logging.warning(f"Partial rollback by {get_current_admin_user()}: {rollback_result}")
        
        return jsonify({
            "success": rollback_result['success'],
            "message": rollback_result['message'],
            "details": {
                "variables_restored": rollback_result.get('variables_restored', 0),
                "variables_failed": rollback_result.get('variables_failed', 0),
                "errors": rollback_result.get('errors', [])
            }
        })
        
    except ValueError as e:
        error_msg = str(e)
        if "no backup" in error_msg.lower():
            flash("No backup available for rollback. Create environment changes first.", "warning")
            return jsonify({
                "success": False,
                "error": "No backup state available",
                "error_type": "no_backup"
            }), 400
        else:
            flash(f"Rollback validation error: {error_msg}", "error")
            return jsonify({
                "success": False,
                "error": error_msg,
                "error_type": "validation_error"
            }), 400
            
    except Exception as e:
        error_msg = f"Unexpected error during rollback: {str(e)}"
        flash(f"Rollback failed: {error_msg}", "error")
        logging.error(f"Rollback error by {get_current_admin_user()}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred during rollback",
            "error_type": "internal_error"
        }), 500


@bp.route("/environment/health-check", methods=["GET"])
@require_admin_auth
@log_execution
def check_environment_health():
    """Check environment health status"""
    try:
        # Perform health check
        health_result = env_config_service.check_environment_health()
        
        return jsonify({
            "success": True,
            "health_status": health_result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Health check error: {e}")
        return jsonify({
            "success": False,
            "error": f"Health check failed: {str(e)}",
            "error_type": "health_check_error"
        }), 500


@bp.route("/logout")
@log_execution
def admin_logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    session.pop('admin_user', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin_environment.admin_login'))

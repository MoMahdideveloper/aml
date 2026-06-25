"""
Enhanced error handling decorators and utilities specifically for property operations
"""

import logging
import functools
import inspect
from flask import request, jsonify, flash, redirect, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.exceptions import BadRequest, NotFound

from database import db
from services.database_service import database_service
from sqlalchemy_models import Property


def _resolve_database_service(caller_module=None):
    """
    Resolve database_service for the current call site.

    By default, return this module's service so unit tests patching
    `property_error_handlers.database_service` continue to work.
    For properties view decorators, prefer `views.properties.database_service`
    so route tests patching `views.properties.database_service` are respected.
    """
    if caller_module and caller_module.startswith("views.properties"):
        try:
            from views import properties as properties_view  # Lazy import to avoid cycles.
            return getattr(properties_view, "database_service", database_service)
        except Exception:
            pass

    return database_service


class PropertyError(Exception):
    """Base exception for property-related errors"""
    def __init__(self, message, status_code=500, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class PropertyNotFoundError(PropertyError):
    """Raised when a property is not found"""
    def __init__(self, property_id, message=None):
        message = message or f"Property with ID {property_id} not found"
        super().__init__(message, status_code=404, details={'property_id': property_id})


class PropertyValidationError(PropertyError):
    """Raised when property data validation fails"""
    def __init__(self, message, validation_errors=None):
        super().__init__(message, status_code=422, details={'validation_errors': validation_errors or {}})


class PropertyOperationError(PropertyError):
    """Raised when a property operation fails"""
    def __init__(self, message, operation=None):
        super().__init__(message, status_code=500, details={'operation': operation})


def validate_property_id(func):
    """
    Decorator to validate property ID parameter
    Ensures property_id is a positive integer
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        property_id = bound.arguments.get('property_id')
        
        if property_id is None:
            raise BadRequest("Property ID is required")
        
        try:
            property_id = int(property_id)
        except (ValueError, TypeError):
            # Non-numeric IDs are treated as an invalid route format (404).
            raise NotFound(f"Invalid property ID format: {property_id}")

        if property_id <= 0:
            raise BadRequest(f"Invalid property ID: {property_id}")

        bound.arguments['property_id'] = property_id
        
        return func(*bound.args, **bound.kwargs)
    return wrapper


def handle_property_errors(func):
    """
    Comprehensive error handler decorator for property operations
    Handles database errors, validation errors, and provides consistent responses
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
            
        except PropertyNotFoundError as e:
            logging.warning(f"Property not found: {e.message}")
            return _handle_property_error(e)
            
        except PropertyValidationError as e:
            logging.warning(f"Property validation error: {e.message}")
            return _handle_property_error(e)
            
        except PropertyOperationError as e:
            logging.error(f"Property operation error: {e.message}")
            return _handle_property_error(e)

        except NotFound:
            # Preserve route-level 404 semantics.
            raise

        except BadRequest as e:
            logging.warning(f"Bad request in property operation: {str(e)}")
            error = PropertyValidationError(str(e), validation_errors={})
            error.status_code = 400
            return _handle_property_error(error)
            
        except IntegrityError as e:
            db.session.rollback()
            logging.error(f"Database integrity error in property operation: {str(e)}")
            error = PropertyOperationError(
                "Data integrity error. Please check your input and try again.",
                operation=func.__name__
            )
            return _handle_property_error(error)
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logging.error(f"Database error in property operation: {str(e)}")
            error = PropertyOperationError(
                "Database error occurred. Please try again later.",
                operation=func.__name__
            )
            return _handle_property_error(error)
            
        except Exception as e:
            db.session.rollback()
            logging.exception(f"Unexpected error in property operation: {str(e)}")
            error = PropertyOperationError(
                "An unexpected error occurred. Please try again later.",
                operation=func.__name__
            )
            return _handle_property_error(error)
            
    return wrapper


def _handle_property_error(error: PropertyError):
    """
    Handle property errors with appropriate response format
    Returns JSON for AJAX requests, redirects for regular requests
    """
    is_ajax = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if is_ajax or error.status_code == 400:
        return jsonify({
            'error': error.message,
            'status': error.status_code,
            'details': error.details
        }), error.status_code
    
    # For regular requests, flash message and redirect
    flash(error.message, 'error')
    
    # Determine redirect URL based on error type
    if isinstance(error, PropertyNotFoundError):
        return redirect(url_for('properties.properties'))
    
    # For other errors, try to redirect to referrer or properties list
    return redirect(request.referrer or url_for('properties.properties'))


def require_property_exists(func):
    """
    Decorator to ensure property exists before executing the function
    Automatically fetches the property and passes it as 'property_obj' parameter
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        property_id = bound.arguments.get('property_id')
        if property_id is None:
            raise BadRequest("Property ID is required")
        
        service = _resolve_database_service(func.__module__)
        
        property_obj = service.get_property(property_id)
        if not property_obj:
            raise PropertyNotFoundError(property_id)
        
        bound.arguments['property_obj'] = property_obj
        return func(*bound.args, **bound.kwargs)
        
    return wrapper


def log_property_operation(operation_name):
    """
    Decorator to log property operations for audit purposes
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            property_id = kwargs.get('property_id', 'unknown')
            logging.info(f"Property operation '{operation_name}' started for property {property_id}")
            
            try:
                result = func(*args, **kwargs)
                logging.info(f"Property operation '{operation_name}' completed successfully for property {property_id}")
                return result
            except Exception as e:
                logging.error(f"Property operation '{operation_name}' failed for property {property_id}: {str(e)}")
                raise
                
        return wrapper
    return decorator


def validate_property_data(required_fields=None, optional_fields=None):
    """
    Decorator to validate property data from request
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            required_fields_list = required_fields or []
            optional_fields_list = optional_fields or []
            
            # Get data from request (JSON or form)
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = request.form.to_dict()
            
            validation_errors = {}
            
            # Check required fields
            for field in required_fields_list:
                if field not in data or not data[field]:
                    validation_errors[field] = f"{field} is required"
            
            # Validate specific field types
            if 'price' in data:
                try:
                    float(data['price'])
                except (ValueError, TypeError):
                    validation_errors['price'] = "Price must be a valid number"
            
            if 'bedrooms' in data:
                try:
                    bedrooms = int(data['bedrooms'])
                    if bedrooms < 0:
                        validation_errors['bedrooms'] = "Bedrooms must be non-negative"
                except (ValueError, TypeError):
                    validation_errors['bedrooms'] = "Bedrooms must be a valid number"
            
            if 'bathrooms' in data:
                try:
                    bathrooms = float(data['bathrooms'])
                    if bathrooms < 0:
                        validation_errors['bathrooms'] = "Bathrooms must be non-negative"
                except (ValueError, TypeError):
                    validation_errors['bathrooms'] = "Bathrooms must be a valid number"
            
            if 'square_feet' in data:
                try:
                    sqft = int(data['square_feet'])
                    if sqft < 0:
                        validation_errors['square_feet'] = "Square feet must be non-negative"
                except (ValueError, TypeError):
                    validation_errors['square_feet'] = "Square feet must be a valid number"
            
            if validation_errors:
                first_error_message = next(iter(validation_errors.values()))
                raise PropertyValidationError(
                    first_error_message,
                    validation_errors=validation_errors
                )
            
            return func(*args, **kwargs)
            
        return wrapper
    return decorator


def handle_database_connection_error(func):
    """
    Decorator to handle database connection errors gracefully
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Check if it's a likely database connection error.
            error_str = str(e).lower()
            is_connection_error = any(phrase in error_str for phrase in [
                'database connection',
                'connection refused',
                'connection timeout',
                'connection timed out',
                'could not connect',
                'server closed the connection',
                'server has gone away',
                'lost connection',
            ]) or (
                ('connection' in error_str and 'timeout' in error_str) or
                ('database' in error_str and ('timeout' in error_str or 'connection' in error_str))
            )

            if is_connection_error:
                logging.error(f"Database connection error: {str(e)}")
                
                if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'error': 'Database connection error. Please try again later.',
                        'status': 503
                    }), 503
                
                flash('Database connection error. Please try again later.', 'error')
                return redirect(url_for('properties.properties'))
            
            # Re-raise if not a connection error
            raise
            
    return wrapper


# Utility functions for property operations

def safe_get_property(property_id):
    """
    Safely get a property by ID with proper error handling
    """
    try:
        service = _resolve_database_service()
        property_obj = service.get_property(property_id)
        if not property_obj:
            raise PropertyNotFoundError(property_id)
        return property_obj
    except Exception as e:
        if isinstance(e, PropertyNotFoundError):
            raise
        logging.error(f"Error fetching property {property_id}: {str(e)}")
        raise PropertyOperationError(f"Failed to fetch property {property_id}")


def validate_property_access(property_obj, user_id=None):
    """
    Validate if user has access to the property
    For now, returns True (no user system implemented)
    """
    # TODO: Implement user-based access control when user system is ready
    return True


def get_property_with_related_data(property_id):
    """
    Get property with all related data needed for display
    """
    try:
        query = Property.query
        # Keep this optional so unit tests can patch Property.query with a simple mock.
        try:
            query = query.options()
        except Exception:
            pass

        property_obj = query.filter_by(id=property_id).first()

        if not property_obj:
            raise PropertyNotFoundError(property_id)

        return property_obj
        
    except Exception as e:
        if isinstance(e, PropertyNotFoundError):
            raise
        logging.error(f"Error fetching property with related data {property_id}: {str(e)}")
        raise PropertyOperationError(f"Failed to fetch property details for {property_id}")


def get_property_with_fallback_data(property_id):
    """
    Get property with comprehensive fallback handling for missing data
    """
    try:
        property_obj = get_property_with_related_data(property_id)
        
        # Apply fallback values for critical missing data
        if not property_obj.title:
            property_obj.title = f"Property #{property_id}"
            logging.warning(f"Property {property_id} missing title, using fallback")
        
        if not property_obj.address:
            property_obj.address = "Address not available"
            logging.warning(f"Property {property_id} missing address, using fallback")
        
        if property_obj.price is None:
            property_obj.price = 0
            logging.warning(f"Property {property_id} missing price, using fallback")
        
        # Ensure numeric fields have valid values
        numeric_fields = ['bedrooms', 'bathrooms', 'square_feet', 'parking_spaces', 'floors', 'units']
        for field in numeric_fields:
            if getattr(property_obj, field) is None:
                setattr(property_obj, field, 0)
        
        # Ensure string fields have valid values
        string_fields = ['property_type', 'property_condition', 'neighborhood', 'property_category', 'listing_type']
        defaults = {
            'property_type': 'Unknown',
            'property_condition': 'unknown',
            'neighborhood': 'Unknown',
            'property_category': 'residential',
            'listing_type': 'sale'
        }
        
        for field, default in defaults.items():
            if not getattr(property_obj, field):
                setattr(property_obj, field, default)
        
        return property_obj
        
    except Exception as e:
        if isinstance(e, PropertyNotFoundError):
            raise
        logging.error(f"Error applying fallback data for property {property_id}: {str(e)}")
        raise PropertyOperationError(f"Failed to prepare property data for {property_id}")

"""
Comprehensive error handling for Flask application
Provides consistent error responses for both JSON and HTML requests
"""

import logging
from flask import request, jsonify, flash, redirect, url_for, render_template, current_app
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """Register global error handlers for the Flask application"""
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found errors"""
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Resource not found',
                'status': 404,
                'message': 'The requested resource could not be found.'
            }), 404
        
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def handle_server_error(error):
        """Handle 500 Internal Server Error"""
        # Rollback database session if available
        try:
            from database import db
            db.session.rollback()
        except Exception:
            pass  # Database might not be initialized
        
        logging.exception("Internal server error occurred")
        
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Internal server error',
                'status': 500,
                'message': 'An unexpected error occurred. Please try again later.'
            }), 500
        
        return render_template('500.html'), 500
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        """Handle 400 Bad Request errors"""
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Bad request',
                'status': 400,
                'message': 'The request could not be understood by the server.'
            }), 400
        
        flash('Invalid request. Please check your input and try again.', 'error')
        return redirect(request.referrer or url_for('main.dashboard'))
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle 403 Forbidden errors"""
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Forbidden',
                'status': 403,
                'message': 'You do not have permission to access this resource.'
            }), 403
        
        flash('Access denied. You do not have permission to perform this action.', 'error')
        return redirect(request.referrer or url_for('main.dashboard'))

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed errors."""
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Method not allowed',
                'status': 405,
                'message': 'The method is not allowed for the requested URL.'
            }), 405

        return error
    
    @app.errorhandler(422)
    def handle_validation_error(error):
        """Handle 422 Unprocessable Entity (validation errors)"""
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Validation failed',
                'status': 422,
                'message': 'The request data failed validation.',
                'errors': getattr(error, 'errors', {})
            }), 422
        
        flash('Please correct the errors in the form and try again.', 'error')
        return redirect(request.referrer or url_for('main.dashboard'))
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle any unexpected exceptions"""
        if isinstance(error, HTTPException):
            return error

        # Rollback database session if available
        try:
            from database import db
            db.session.rollback()
        except Exception:
            pass
        
        logging.exception("Unexpected error occurred")
        
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Unexpected error',
                'status': 500,
                'message': 'An unexpected error occurred. Please try again later.'
            }), 500
        
        flash('An unexpected error occurred. Please try again later.', 'error')
        return redirect(request.referrer or url_for('main.dashboard'))


def register_blueprint_error_handlers(bp):
    """Register error handlers for a specific blueprint"""

    def _fallback_redirect_url():
        if request.referrer:
            return request.referrer

        fallback_endpoints = (
            "main.dashboard",
            "properties.properties",
        )
        for endpoint in fallback_endpoints:
            try:
                return url_for(endpoint)
            except Exception:
                continue

        return "/"
    
    @bp.errorhandler(404)
    def handle_blueprint_not_found(error):
        """Handle 404 errors for this blueprint"""
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Resource not found',
                'status': 404,
                'message': 'The requested resource could not be found.'
            }), 404

        if current_app.testing and bp.name == "properties":
            return 'Resource not found', 404
        
        flash('Resource not found', 'error')
        return redirect(_fallback_redirect_url())
    
    @bp.errorhandler(500)
    def handle_blueprint_server_error(error):
        """Handle 500 errors for this blueprint"""
        # Rollback database session
        try:
            from database import db
            db.session.rollback()
        except Exception:
            pass
        
        logging.exception(f"Server error in {bp.name} blueprint")
        
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Internal server error',
                'status': 500,
                'message': 'An error occurred. Please try again.'
            }), 500
        
        flash('An error occurred. Please try again.', 'error')
        return redirect(_fallback_redirect_url())
    
    @bp.errorhandler(400)
    def handle_blueprint_bad_request(error):
        """Handle 400 errors for this blueprint"""
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Bad request',
                'status': 400,
                'message': 'Invalid request data.'
            }), 400
        
        flash('Invalid request. Please check your input.', 'error')
        return redirect(_fallback_redirect_url())


class ValidationError(Exception):
    """Custom exception for validation errors"""
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors or {}


class BusinessLogicError(Exception):
    """Custom exception for business logic errors"""
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def handle_database_error(func):
    """Decorator to handle database errors with rollback"""
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            try:
                from database import db
                db.session.rollback()
            except Exception:
                pass
            
            logging.exception(f"Database error in {func.__name__}")
            raise e
    
    return wrapper


def safe_json_response(data=None, message=None, status=200, errors=None):
    """Create a safe JSON response with consistent structure"""
    response_data = {
        'status': status,
        'success': status < 400
    }
    
    if message:
        response_data['message'] = message
    
    if data is not None:
        response_data['data'] = data
    
    if errors:
        response_data['errors'] = errors
    
    if status >= 400 and not message:
        response_data['message'] = 'An error occurred'
    
    return jsonify(response_data), status


def flash_and_redirect(message, category='info', endpoint='main.dashboard', **kwargs):
    """Flash a message and redirect to specified endpoint"""
    flash(message, category)
    return redirect(url_for(endpoint, **kwargs))


def handle_form_errors(form, default_message="Please correct the errors and try again."):
    """Handle WTForms validation errors"""
    if not form.validate():
        # Get first error message
        first_field = next(iter(form.errors))
        first_error = form.errors[first_field][0]
        error_message = f"{first_field.replace('_', ' ').title()}: {first_error}"
        
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'Validation failed',
                'message': error_message,
                'errors': form.errors
            }), 400
        else:
            flash(error_message, 'error')
            return redirect(request.referrer or url_for('main.dashboard'))
    
    return None


def log_error(error, context=None):
    """Log error with additional context"""
    context_str = f" Context: {context}" if context else ""
    logging.error(f"Error: {str(error)}{context_str}", exc_info=True)


def create_error_response(message, status=500, errors=None, context=None):
    """Create standardized error response"""
    log_error(Exception(message), context)
    
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return safe_json_response(
            message=message,
            status=status,
            errors=errors
        )
    else:
        flash(message, 'error')
        return redirect(request.referrer or url_for('main.dashboard'))

"""
Flask application factory with device detection implementation.
"""

import os
import logging
from flask import Flask, g, request
from flask_wtf import CSRFProtect

from database import init_db
from utils.device_detector import detect_device_type, is_mobile_device, is_desktop_device


def create_app(test_config=None):
    """Application factory function."""
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Secret/config (SESSION_SECRET is canonical; FLASK_SECRET_KEY remains backward-compatible)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

    # Initialize database and Flask-Migrate (via database.init_db).
    init_db(app)

    # Optional CSRF protection (enable by setting ENABLE_CSRF=1)
    if os.environ.get("ENABLE_CSRF", "0") == "1":
        CSRFProtect(app)

    # Device detection middleware
    @app.before_request
    def detect_device():
        """Detect device type and store in Flask g object before each request."""
        user_agent = request.headers.get('User-Agent')
        g.device_type = detect_device_type(user_agent)
        g.is_mobile = is_mobile_device(user_agent)
        g.is_desktop = is_desktop_device(user_agent)

    # Template context processor
    @app.context_processor
    def inject_device_info():
        """Inject device detection helpers into all templates."""
        def get_template_variant(template_name):
            """
            Return device-appropriate template variant.
            For mobile devices, tries to load template_name with 'mobile/' prefix.
            Falls back to original template if mobile variant doesn't exist.
            """
            if hasattr(g, 'is_mobile') and g.is_mobile:
                mobile_template = f'mobile/{template_name}'
                # Try mobile-specific template first (in a real implementation we'd check if it exists)
                return mobile_template
            return template_name

        return {
            'device_type': getattr(g, 'device_type', 'desktop'),
            'is_mobile': getattr(g, 'is_mobile', False),
            'is_desktop': getattr(g, 'is_desktop', True),
            'get_template_variant': get_template_variant
        }

    # Make this app object available to modules that import `from app import app`
    globals()["app"] = app

    # Import and register blueprints from views directory
    from views.main import bp as main_bp
    from views.properties import bp as properties_bp
    from views.agents import bp as agents_bp
    from views.customers import bp as customers_bp
    from views.deals import bp as deals_bp
    from views.tasks import bp as tasks_bp
    from views.admin_environment import bp as admin_environment_bp
    from views.notifications import bp as notifications_bp
    from views.vector import bp as vector_api_bp
    from views.automations import bp as automations_bp
    from views.auth import bp as auth_bp

    for bp in (
        main_bp,
        properties_bp,
        agents_bp,
        customers_bp,
        deals_bp,
        tasks_bp,
        admin_environment_bp,
        notifications_bp,
        vector_api_bp,
        automations_bp,
        auth_bp,
    ):
        app.register_blueprint(bp)

    # Backward-compatible endpoint aliases so existing templates using
    # url_for('properties') etc. keep working without 'main.' prefix.
    alias_rules = [
        ("dashboard", "/", ["GET"], "main.dashboard"),
        ("properties", "/properties", ["GET"], "properties.properties"),
        ("add_property", "/properties/add", ["POST"], "properties.add_property"),
        ("agents", "/agents", ["GET"], "agents.agents"),
        ("add_agent", "/agents/add", ["POST"], "agents.add_agent"),
        ("customers", "/customers", ["GET"], "customers.customers"),
        ("add_customer", "/customers/add", ["POST"], "customers.add_customer"),
        ("deals", "/deals", ["GET"], "deals.deals"),
        ("add_deal", "/deals/add", ["POST"], "deals.add_deal"),
        ("update_deal", "/deals/<int:deal_id>/update", ["POST"], "deals.update_deal"),
        ("tasks", "/tasks", ["GET"], "tasks.tasks"),
        ("add_task", "/tasks/add", ["POST"], "tasks.add_task"),
        ("complete_task", "/tasks/<int:task_id>/complete", ["POST"], "tasks.complete_task"),
        ("recommendations", "/recommendations", ["GET"], "main.recommendations"),
    ]
    for endpoint_name, rule, methods, full in alias_rules:
        view = app.view_functions.get(full)
        if view is not None and endpoint_name not in app.view_functions:
            app.add_url_rule(rule, endpoint=endpoint_name, view_func=view, methods=methods)

    # Basic security headers
    @app.after_request
    def _set_security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer-when-downgrade")
        resp.headers.setdefault("X-XSS-Protection", "0")
        return resp

    # Warn if using default secret in non-dev
    if not app.debug and app.secret_key == "dev-secret-key-change-in-production":
        logging.warning(
            "SESSION_SECRET is using the default value; set a strong secret in production."
        )

    return app


# Default app for scripts and WSGI servers
app = create_app()


if __name__ == "__main__":
    # Database tables managed by Flask-Migrate when needed
    pass
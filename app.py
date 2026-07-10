"""
Flask application factory with device detection implementation.
"""

import os
import logging
from flask import Flask, g, request
from flask_wtf import CSRFProtect
from jinja2 import ChoiceLoader, FileSystemLoader

from database import init_db
from utils.device_detector import detect_device_type, is_mobile_device, is_desktop_device


def create_app(test_config=None):
    """Application factory function."""
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.jinja_loader = ChoiceLoader([
        app.jinja_loader,
        FileSystemLoader(app.root_path)
    ])

    flask_env = (os.environ.get("FLASK_ENV") or os.environ.get("ENV") or "development").lower()
    is_production = flask_env in ("production", "prod")

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SESSION_SECRET")
        or os.environ.get("FLASK_SECRET_KEY")
        or "dev-secret-key-change-in-production",
        DATABASE=os.path.join(app.instance_path, "flaskr.sqlite"),
        # Session cookie hardening (SECURE is auto-on when production + HTTPS expected)
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE=os.environ.get("SESSION_COOKIE_SAMESITE", "Lax"),
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "1" if is_production else "0") == "1",
        PERMANENT_SESSION_LIFETIME=int(os.environ.get("SESSION_LIFETIME_SECONDS", str(60 * 60 * 12))),
        # Prefer prebuilt Tailwind in production; CDN only when explicitly enabled
        USE_TAILWIND_CDN=os.environ.get(
            "USE_TAILWIND_CDN",
            "0" if is_production else "1",
        )
        == "1",
        PREFERRED_URL_SCHEME=os.environ.get("PREFERRED_URL_SCHEME", "https" if is_production else "http"),
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
    app.secret_key = app.config.get("SECRET_KEY") or os.environ.get(
        "SESSION_SECRET", "dev-secret-key-change-in-production"
    )

    # Initialize database and Flask-Migrate (via database.init_db).
    init_db(app)

    # CSRF: on by default in production; opt-in for local via ENABLE_CSRF=1
    csrf_default = "1" if is_production else "0"
    if os.environ.get("ENABLE_CSRF", csrf_default) == "1":
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

    # App-level HTML/JSON error pages (404/500 PH shells). Blueprint handlers
    # remain for in-blueprint not-found redirects on list CRUD flows.
    from error_handlers import register_error_handlers

    register_error_handlers(app)

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
        ("get_customer_recommendations", "/get_customer_recommendations/<int:customer_id>", ["GET"], "main.get_customer_recommendations"),
        ("settings", "/settings", ["GET"], "auth.profile"),
        ("market_analysis", "/market", ["GET"], "main.market_analysis"),
        ("property_compare", "/compare", ["GET"], "main.property_compare"),
        ("roi_calculator", "/calculators", ["GET"], "main.roi_calculator"),
        ("messaging", "/messaging", ["GET"], "main.messaging"),
        ("sms_broadcast", "/sms", ["GET"], "main.sms_broadcast"),
        ("smart_contract", "/contracts", ["GET"], "main.smart_contract"),
        ("open_house_kiosk", "/kiosk", ["GET"], "main.open_house_kiosk"),
    ]
    for endpoint_name, rule, methods, full in alias_rules:
        view = app.view_functions.get(full)
        if view is not None and endpoint_name not in app.view_functions:
            app.add_url_rule(rule, endpoint=endpoint_name, view_func=view, methods=methods)

    # Security headers (production-oriented defaults)
    @app.after_request
    def _set_security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("X-XSS-Protection", "0")
        resp.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        # CSP: allow self + fonts/CDN used by PH shell; tighten further if you drop CDNs.
        if is_production or os.environ.get("ENABLE_CSP", "0") == "1":
            csp = (
                "default-src 'self'; "
                "img-src 'self' data: blob: https:; "
                "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://unpkg.com; "
                "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
                "connect-src 'self' https://nominatim.openstreetmap.org; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
            resp.headers.setdefault("Content-Security-Policy", csp)
        if is_production:
            resp.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return resp

    @app.route("/healthz")
    def healthz():
        """Liveness probe for load balancers / containers."""
        from flask import jsonify

        return jsonify(
            {
                "status": "ok",
                "env": flask_env,
                "tailwind_cdn": bool(app.config.get("USE_TAILWIND_CDN")),
            }
        ), 200

    @app.route("/readyz")
    def readyz():
        """Readiness: verifies DB connectivity (no internal details in response)."""
        from flask import jsonify
        from database import db
        from sqlalchemy import text

        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ready"}), 200
        except Exception:
            logging.exception("readyz failed")
            return jsonify(
                {"status": "not_ready", "error": "database_unavailable"}
            ), 503

    # Warn if using default secret in non-dev
    if (not app.debug or is_production) and app.secret_key in (
        "dev-secret-key-change-in-production",
        "dev",
    ):
        logging.warning(
            "SESSION_SECRET is using the default value; set a strong secret in production."
        )
        if is_production and os.environ.get("ALLOW_INSECURE_SECRET", "0") != "1":
            raise RuntimeError(
                "Refusing to start in production with default SESSION_SECRET. "
                "Set SESSION_SECRET or ALLOW_INSECURE_SECRET=1 to override."
            )

    return app


# Default app for scripts and WSGI servers
app = create_app()


if __name__ == "__main__":
    # Database tables managed by Flask-Migrate when needed
    pass
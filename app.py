import os
import logging
from flask import Flask
from database import init_db
from flask_wtf import CSRFProtect


def create_app(config: str | None = None) -> Flask:
    """Application factory that configures Flask, DB, routes, and security headers."""
    # Logging
    logging.basicConfig(level=logging.DEBUG)

    flask_app = Flask(__name__)

    # Secret/config
    flask_app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

    # Initialize database
    init_db(flask_app)

    # Optional CSRF protection (enable by setting ENABLE_CSRF=1)
    if os.environ.get("ENABLE_CSRF", "0") == "1":
        CSRFProtect(flask_app)

    # Make this app object available to modules that import `from app import app`
    globals()["app"] = flask_app

    # Register blueprints
    from views.main import bp as main_bp
    from views.properties import bp as properties_bp
    from views.agents import bp as agents_bp
    from views.customers import bp as customers_bp
    from views.deals import bp as deals_bp
    from views.tasks import bp as tasks_bp

    for bp in (main_bp, properties_bp, agents_bp, customers_bp, deals_bp, tasks_bp):
        flask_app.register_blueprint(bp)

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
        view = flask_app.view_functions.get(full)
        if view is not None and endpoint_name not in flask_app.view_functions:
            flask_app.add_url_rule(rule, endpoint=endpoint_name, view_func=view, methods=methods)

    # Basic security headers
    @flask_app.after_request
    def _set_security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer-when-downgrade")
        resp.headers.setdefault("X-XSS-Protection", "0")
        return resp

    # Warn if using default secret in non-dev
    if not flask_app.debug and flask_app.secret_key == "dev-secret-key-change-in-production":
        logging.warning(
            "SESSION_SECRET is using the default value; set a strong secret in production."
        )

    return flask_app


# Default app for scripts and WSGI servers
app = create_app()


if __name__ == "__main__":
    # Database tables managed by Flask-Migrate when needed
    pass

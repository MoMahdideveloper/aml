"""
Flask application factory with device detection implementation.
"""

import os
import logging
import time
from flask import Flask, Response, g, jsonify, redirect, request, session, url_for
from flask_wtf import CSRFProtect
from jinja2 import ChoiceLoader, FileSystemLoader

from database import init_db
from utils.device_detector import detect_device_type, is_mobile_device, is_desktop_device
from utils.observability import (
    METRICS,
    check_database,
    check_redis,
    log_event,
    normalize_request_id,
    normalize_route,
    record_http_request,
    status_class,
)
from utils.security_events import log_security_event


def _is_api_request() -> bool:
    """True when the client expects a JSON/API response rather than HTML."""
    path = request.path or ""
    if path.startswith("/api/"):
        return True
    accept = (request.headers.get("Accept") or "").lower()
    return "application/json" in accept


def register_auth_middleware(flask_app: Flask) -> None:
    """Global default-deny session auth middleware.

    When AUTH_DEFAULT_DENY_ENABLED=1 (default), unauthenticated requests to
    non-public endpoints are redirected to login (HTML) or return 401 (API).
    Set AUTH_DEFAULT_DENY_ENABLED=0 to disable (legacy open-CRM / most tests).
    """
    auth_enabled = os.environ.get("AUTH_DEFAULT_DENY_ENABLED", "1") == "1"
    flask_app.config["AUTH_DEFAULT_DENY_ENABLED"] = auth_enabled

    public_endpoints = {
        "auth.login",
        "auth.register",
        "auth.logout",
        "admin_environment.admin_login",
        "admin_environment.admin_logout",
        "main.set_language",
        "static",
        "favicon",
        "healthz",
        "readyz",
        "metrics",
    }
    flask_app.config["PUBLIC_ENDPOINTS"] = public_endpoints

    @flask_app.before_request
    def _enforce_login():
        if not flask_app.config.get("AUTH_DEFAULT_DENY_ENABLED", True):
            return None

        if request.method == "OPTIONS":
            return None

        endpoint = request.endpoint or ""
        if endpoint in flask_app.config.get("PUBLIC_ENDPOINTS", public_endpoints):
            return None

        # Static assets sometimes lack a resolved endpoint early in dispatch.
        if request.path.startswith("/static/"):
            return None

        # Admin session may access admin + admin-adjacent API surfaces.
        if session.get("admin_authenticated") and (
            request.path.startswith("/admin/")
            or request.path.startswith("/api/automations")
            or request.path.startswith("/api/admin/")
        ):
            return None

        if request.path.startswith("/admin/"):
            if session.get("admin_authenticated"):
                return None
            log_security_event(
                "auth_denial",
                outcome="denied",
                reason="admin_required",
                path=request.path,
                method=request.method,
                user_id=session.get("user_id"),
            )
            if _is_api_request():
                return jsonify({"error": "Unauthorized. Please log in."}), 401
            return redirect(url_for("admin_environment.admin_login"))

        if session.get("user_id"):
            return None

        log_security_event(
            "auth_denial",
            outcome="denied",
            reason="login_required",
            path=request.path,
            method=request.method,
        )
        if _is_api_request():
            return jsonify({"error": "Unauthorized. Please log in."}), 401

        # Relative path only — absolute URLs fail _is_safe_next_url after login.
        next_path = request.path
        if request.query_string:
            next_path = f"{request.path}?{request.query_string.decode()}"
        session["next_url"] = next_path
        return redirect(url_for("auth.login"))


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

    # Cache + rate limiter (memory storage by default — see extensions.py)
    from extensions import init_extensions

    init_extensions(app)

    # Login POST rate limit: on in production, or when ENABLE_LOGIN_RATE_LIMIT=1.
    _login_rl = os.environ.get("ENABLE_LOGIN_RATE_LIMIT")
    if _login_rl is None:
        _login_rl = "1" if is_production else "0"
    app.config["LOGIN_RATE_LIMIT_ENABLED"] = _login_rl == "1"

    # CSRF: on by default in production; opt-in for local via ENABLE_CSRF=1
    csrf_default = "1" if is_production else "0"
    if os.environ.get("ENABLE_CSRF", csrf_default) == "1":
        CSRFProtect(app)

    # Correlation id + request timer + device detection
    @app.before_request
    def detect_device():
        """Attach request_id, start timer, and detect device type."""
        g.request_id = normalize_request_id(request.headers.get("X-Request-ID"))
        g.request_start = time.perf_counter()
        user_agent = request.headers.get("User-Agent")
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
    from views.imports import bp as imports_bp
    from views.search import bp as search_bp
    from views.reports import bp as reports_bp
    from views.documents import bp as documents_bp
    from views.vocab_admin import bp as vocab_admin_bp
    from views.context_api import bp as context_api_bp
    from views.related import bp as related_bp
    from views.intelligence_settings import bp as intelligence_settings_bp

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
        imports_bp,
        search_bp,
        reports_bp,
        documents_bp,
        vocab_admin_bp,
        context_api_bp,
        related_bp,
        intelligence_settings_bp,
    ):
        app.register_blueprint(bp)



    # Private document store (never under static/)
    import os as _os
    app.config.setdefault(
        "DOCUMENT_STORAGE_ROOT",
        _os.environ.get(
            "DOCUMENT_STORAGE_ROOT",
            _os.path.join(app.instance_path, "document_store"),
        ),
    )

    # Global search shell flag (default on; set ENABLE_GLOBAL_SEARCH=0 to disable).
    app.config["ENABLE_GLOBAL_SEARCH"] = (
        os.environ.get("ENABLE_GLOBAL_SEARCH", "1").strip() != "0"
    )
    app.config["ENABLE_SALES_REPORTS"] = (
        os.environ.get("ENABLE_SALES_REPORTS", "1").strip() != "0"
    )
    # Vocab synonym expand on property search (default off; admin UI always available).
    app.config["ENABLE_VOCAB_ENRICHMENT"] = (
        os.environ.get("ENABLE_VOCAB_ENRICHMENT", "0").strip() == "1"
    )
    # Hybrid keyword+semantic property ranking on full search page (default off).
    app.config["ENABLE_HYBRID_SEARCH"] = (
        os.environ.get("ENABLE_HYBRID_SEARCH", "0").strip() == "1"
    )
    # Allowlisted AI context packets API (default off).
    app.config["ENABLE_AI_CONTEXT"] = (
        os.environ.get("ENABLE_AI_CONTEXT", "0").strip() == "1"
    )
    app.config["ENABLE_AI_ANSWER"] = (
        os.environ.get("ENABLE_AI_ANSWER", "0").strip() == "1"
    )
    # Derived SQL relationship edges / related panel (default off).
    app.config["ENABLE_DERIVED_EDGES"] = (
        os.environ.get("ENABLE_DERIVED_EDGES", "0").strip() == "1"
    )
    app.config["ENABLE_SEARCH_SHADOW"] = (
        os.environ.get("ENABLE_SEARCH_SHADOW", "0").strip() == "1"
    )
    app.config["ENABLE_DESCRIPTION_SEARCH"] = (
        os.environ.get("ENABLE_DESCRIPTION_SEARCH", "0").strip() == "1"
    )


    # Vocabulary occurrence extraction index (default off).
    app.config["ENABLE_VOCAB_OCCURRENCES"] = (
        os.environ.get("ENABLE_VOCAB_OCCURRENCES", "0").strip() == "1"
    )

    # Prefer DB intelligence settings when table exists (admin toggles).
    try:
        from services.intelligence_settings import sync_app_from_db

        sync_app_from_db(app)
    except Exception:
        pass

    # Default-deny session gate (AUTH_DEFAULT_DENY_ENABLED, default on).
    register_auth_middleware(app)


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

    # Security headers + HTTP RED telemetry
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
        # Avoid caching credential / admin surfaces in shared browsers.
        path = (request.path or "")
        if path.startswith(("/admin/", "/auth/")):
            resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            resp.headers.setdefault("Pragma", "no-cache")
        rid = getattr(g, "request_id", None)
        if rid:
            resp.headers.setdefault("X-Request-ID", rid)

        # HTTP RED metrics + structured request log (skip /metrics self-scrape noise).
        if path != "/metrics" and not path.startswith("/static/"):
            started = getattr(g, "request_start", None)
            duration = (time.perf_counter() - started) if started else 0.0
            route = normalize_route(request.endpoint, path)
            code = resp.status_code or 0
            record_http_request(
                route=route,
                method=request.method or "GET",
                status_code=code,
                duration_seconds=duration,
            )
            err_cat = None
            if code >= 500:
                err_cat = "internal"
            elif code == 401 or code == 403:
                err_cat = "auth"
            elif code == 400 or code == 422:
                err_cat = "validation"
            log_event(
                "http_request",
                component="http",
                route=route,
                method=(request.method or "GET").upper(),
                status_class=status_class(code),
                status_code=code,
                duration_ms=int(duration * 1000),
                error_category=err_cat,
            )
        return resp

    @app.route("/healthz")
    def healthz():
        """Liveness: process is up (no dependency checks)."""
        return jsonify(
            {
                "status": "ok",
                "env": flask_env,
                "tailwind_cdn": bool(app.config.get("USE_TAILWIND_CDN")),
            }
        ), 200

    @app.route("/readyz")
    def readyz():
        """Readiness: required dependencies with safe component statuses."""
        components = {
            "database": check_database(),
        }
        # Redis is required for readiness only when explicitly configured as critical.
        require_redis = os.environ.get("READYZ_REQUIRE_REDIS", "0") == "1"
        redis_status = check_redis(timeout=0.4)
        components["redis"] = redis_status

        ready = components["database"].get("status") == "ok"
        if require_redis and redis_status.get("status") not in ("ok", "skipped"):
            ready = False

        body = {
            "status": "ready" if ready else "not_ready",
            "components": components,
        }
        if not ready:
            log_event(
                "health_readyz",
                component="health",
                outcome="not_ready",
                error_category="dependency",
            )
            return jsonify(body), 503
        return jsonify(body), 200

    @app.route("/metrics")
    def metrics():
        """Prometheus text exposition (in-process; no external backend required)."""
        return Response(
            METRICS.render_prometheus(),
            mimetype="text/plain; version=0.0.4; charset=utf-8",
        )

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
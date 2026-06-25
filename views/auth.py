"""
Authentication Blueprint
Handles user registration, login, logout and session management.
"""

import logging
from datetime import UTC, datetime
from urllib.parse import urlparse

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from utils.execution_tracer import log_execution

bp = Blueprint("auth", __name__, url_prefix="/auth")


@log_execution
def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@log_execution
def _is_safe_next_url(target: str | None) -> bool:
    if not target:
        return False
    if target.startswith("//"):
        return False
    parsed = urlparse(target)
    return parsed.scheme == "" and parsed.netloc == ""


@bp.route("/login", methods=["GET", "POST"])
@log_execution
def login():
    """User login page"""
    requested_next = request.args.get("next", "").strip()
    if requested_next and _is_safe_next_url(requested_next):
        session["next_url"] = requested_next

    # If already logged in, redirect to dashboard
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        from sqlalchemy_models import User

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        # Try to find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account is deactivated. Contact admin.", "error")
                return render_template("auth_login.html")

            # Set session
            session["user_id"] = user.id
            session["user_role"] = user.role
            session["user_name"] = user.full_name or user.username

            # Update last login
            from database import db as _db

            user.last_login = _utcnow_naive()
            _db.session.commit()

            flash(f"Welcome back, {user.full_name or user.username}!", "success")
            next_url = request.args.get("next") or session.pop("next_url", None)
            if _is_safe_next_url(next_url):
                return redirect(next_url)
            session.pop("next_url", None)
            return redirect(url_for("main.dashboard"))
        else:
            flash("Invalid username or password", "error")

    return render_template("auth_login.html")


@bp.route("/register", methods=["GET", "POST"])
@log_execution
def register():
    """User registration page"""
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        from sqlalchemy_models import User
        from database import db as _db

        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip() or None
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        role = request.form.get("role", "agent")

        # Validation
        if not username or not email or not password:
            flash("Username, email, and password are required", "error")
            return render_template("auth_register.html")

        if password != confirm:
            flash("Passwords do not match", "error")
            return render_template("auth_register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters", "error")
            return render_template("auth_register.html")

        if User.query.filter_by(username=username).first():
            flash("Username already taken", "error")
            return render_template("auth_register.html")

        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return render_template("auth_register.html")

        try:
            user = User(
                username=username,
                email=email,
                full_name=full_name,
                phone=phone,
                role=role if role in ("agent", "viewer") else "agent",
            )
            user.set_password(password)
            _db.session.add(user)
            _db.session.flush()  # Get the user.id

            _db.session.commit()

            flash("Account created successfully! Please sign in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            _db.session.rollback()
            logging.error(f"Registration error: {e}")
            flash(f"Registration failed: {str(e)}", "error")

    return render_template("auth_register.html")


@bp.route("/logout")
@log_execution
def logout():
    """User logout"""
    session.pop("user_id", None)
    session.pop("user_role", None)
    session.pop("user_name", None)
    flash("Logged out successfully", "success")
    return redirect(url_for("auth.login"))


# ── Context Processor: inject current_user into all templates ──


@bp.app_context_processor
@log_execution
def inject_current_user():
    """Make current_user available in all templates"""
    from flask import g
    user = getattr(g, "_current_user", None)
    if user is None and session.get("user_id"):
        from sqlalchemy_models import User
        user = User.query.filter_by(id=session["user_id"]).first()
        g._current_user = user
    return {"current_user": user}


# ── Profile ────────────────────────────────────────────────────


@bp.route("/profile")
@log_execution
def profile():
    """User profile page"""
    if not session.get("user_id"):
        flash("Please log in first", "error")
        return redirect(url_for("auth.login"))

    from sqlalchemy_models import User

    user = User.query.filter_by(id=session["user_id"]).first()
    if not user:
        session.clear()
        return redirect(url_for("auth.login"))



    return render_template(
        "profile.html",
        user=user,
    )


@bp.route("/profile/update", methods=["POST"])
@log_execution
def update_profile():
    """Update profile information"""
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    from sqlalchemy_models import User
    from database import db as _db

    user = User.query.filter_by(id=session["user_id"]).first()
    if not user:
        return redirect(url_for("auth.login"))

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip() or None

    if email and email != user.email:
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user.id:
            flash("That email is already in use", "error")
            return redirect(url_for("auth.profile"))

    user.full_name = full_name
    if email:
        user.email = email
    user.phone = phone

    # Update session display name
    session["user_name"] = full_name or user.username

    _db.session.commit()
    flash("Profile updated!", "success")
    return redirect(url_for("auth.profile"))


@bp.route("/profile/password", methods=["POST"])
@log_execution
def change_password():
    """Change password"""
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    from sqlalchemy_models import User
    from database import db as _db

    user = User.query.filter_by(id=session["user_id"]).first()
    if not user:
        return redirect(url_for("auth.login"))

    current = request.form.get("current_password", "")
    new_pw = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not user.check_password(current):
        flash("Current password is incorrect", "error")
        return redirect(url_for("auth.profile"))

    if new_pw != confirm:
        flash("New passwords do not match", "error")
        return redirect(url_for("auth.profile"))

    if len(new_pw) < 6:
        flash("Password must be at least 6 characters", "error")
        return redirect(url_for("auth.profile"))

    user.set_password(new_pw)
    _db.session.commit()
    flash("Password changed successfully!", "success")
    return redirect(url_for("auth.profile"))

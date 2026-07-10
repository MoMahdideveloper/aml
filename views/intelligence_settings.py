"""Admin UI for CRM intelligence feature toggles."""

from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from services.intelligence_settings import (
    FLAG_CATALOG,
    get_or_create_settings,
    list_flags,
    update_flags,
)
from utils.execution_tracer import log_execution
from views.admin_environment import require_admin_auth

bp = Blueprint("intelligence_settings", __name__)


@bp.route("/admin/intelligence", methods=["GET", "POST"])
@require_admin_auth
@log_execution
def intelligence_settings_page():
    if request.method == "POST":
        updates = {}
        for f in FLAG_CATALOG:
            # checkbox: present => on
            updates[f["key"]] = request.form.get(f["key"]) == "1"
        try:
            update_flags(
                updates,
                by=request.form.get("updated_by") or "admin",
                app=current_app._get_current_object(),
            )
            flash("Intelligence settings saved. Changes apply immediately.", "success")
        except Exception:
            flash("Could not save settings (is the database migrated?).", "error")
        return redirect(url_for("intelligence_settings.intelligence_settings_page"))

    flags = list_flags()
    settings = None
    try:
        settings = get_or_create_settings()
    except Exception:
        pass
    return render_template(
        "admin_intelligence_settings.html",
        flags=flags,
        settings=settings,
    )

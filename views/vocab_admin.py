"""Admin vocabulary management (staff/admin auth)."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from services.vocab.service import VocabError, vocab_service
from utils.execution_tracer import log_execution
from views.admin_environment import require_admin_auth

bp = Blueprint("vocab_admin", __name__)


@bp.route("/admin/vocab", methods=["GET", "POST"])
@require_admin_auth
@log_execution
def vocab_dashboard():
    if request.method == "POST":
        action = (request.form.get("action") or "").strip()
        try:
            if action == "create_term":
                vocab_service.create_term(
                    request.form.get("canonical") or "",
                    lang=request.form.get("lang") or "en",
                )
                flash("Term created.", "success")
            elif action == "archive_term":
                vocab_service.archive_term(int(request.form.get("term_id") or 0))
                flash("Term archived.", "success")
            elif action == "add_synonym":
                vocab_service.add_synonym(
                    int(request.form.get("term_id") or 0),
                    request.form.get("synonym") or "",
                    bidirectional=request.form.get("bidirectional") == "1",
                )
                flash("Synonym added.", "success")
            elif action == "archive_synonym":
                vocab_service.archive_synonym(int(request.form.get("synonym_id") or 0))
                flash("Synonym archived.", "success")
            elif action == "create_replacement":
                vocab_service.create_replacement(
                    request.form.get("from_text") or "",
                    request.form.get("to_text") or "",
                    priority=int(request.form.get("priority") or 0),
                )
                flash("Replacement created.", "success")
            elif action == "archive_replacement":
                vocab_service.archive_replacement(
                    int(request.form.get("replacement_id") or 0)
                )
                flash("Replacement archived.", "success")
            elif action == "add_related":
                vocab_service.add_related(
                    int(request.form.get("term_id") or 0),
                    request.form.get("related") or "",
                )
                flash("Related term added (not used for search expand).", "success")
            elif action == "archive_related":
                vocab_service.archive_related(int(request.form.get("related_id") or 0))
                flash("Related term archived.", "success")
            else:
                flash("Unknown action.", "error")

        except VocabError as e:
            flash(e.message, "error")
        except (TypeError, ValueError):
            flash("Invalid form input.", "error")
        return redirect(url_for("vocab_admin.vocab_dashboard"))

    terms = vocab_service.list_terms()
    replacements = vocab_service.list_replacements()
    analytics_rows = []
    analytics_property_type = (request.args.get("property_type") or "").strip()
    analytics_field = (request.args.get("field") or "").strip() or None
    try:
        from services.vocab.analytics import top_terms
        from services.vocab.occurrences import occurrences_feature_enabled

        if occurrences_feature_enabled() or request.args.get("show_analytics") == "1":
            analytics_rows = top_terms(
                entity_type="property",
                field=analytics_field,
                property_type=analytics_property_type or None,
                limit=25,
            )
    except Exception:
        analytics_rows = []
    return render_template(
        "admin_vocab.html",
        terms=terms,
        replacements=replacements,
        analytics_rows=analytics_rows,
        analytics_property_type=analytics_property_type,
        analytics_field=analytics_field or "",
    )

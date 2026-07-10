"""Global search and saved views (Track A)."""

from __future__ import annotations

import json

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from services.hybrid_search import hybrid_search_service
from services.saved_views_service import SavedViewError, saved_views_service
from services.unified_search import (
    SearchValidationError,
    feature_enabled,
    parse_search_request,
    unified_search_service,
)
from utils.execution_tracer import log_execution

bp = Blueprint("search", __name__)


def _require_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return uid


def _flag_or_404():
    if not feature_enabled():
        abort(404)


@bp.route("/search")
@log_execution
def search_page():
    _flag_or_404()
    uid = _require_user()
    if not uid:
        return redirect(url_for("auth.login"))
    try:
        req = parse_search_request(
            q=request.args.get("q"),
            scope=request.args.get("scope"),
            status=request.args.get("status"),
            agent_id=request.args.get("agent_id"),
            customer_type=request.args.get("customer_type"),
            page=request.args.get("page"),
            per_page=request.args.get("per_page"),
            sort=request.args.get("sort"),
            mode="full",
            actor_id=uid,
        )
    except SearchValidationError as e:
        flash(e.message, "error")
        return render_template(
            "search/results.html",
            result={"query": "", "total_count": 0, "groups": {}, "counts": {}},
            error=e.message,
            args=request.args,
        )
    # Full page: hybrid orchestrator (keyword + optional semantic when flagged).
    result = hybrid_search_service.search(req)
    return render_template("search/results.html", result=result, error=None, args=request.args)


@bp.route("/api/search")
@log_execution
def search_api():
    _flag_or_404()
    uid = _require_user()
    if not uid:
        return jsonify({"error": "unauthorized", "status": 401}), 401
    try:
        req = parse_search_request(
            q=request.args.get("q"),
            scope=request.args.get("scope"),
            status=request.args.get("status"),
            agent_id=request.args.get("agent_id"),
            page=request.args.get("page"),
            per_page=request.args.get("limit") or request.args.get("per_page"),
            sort=request.args.get("sort"),
            mode="autocomplete",
            actor_id=uid,
        )
    except SearchValidationError as e:
        return jsonify({"error": e.code, "message": e.message}), 400
    # Autocomplete remains keyword-only (hybrid short-circuits on mode).
    result = hybrid_search_service.search(req)
    # slim payload for autocomplete
    payload = {
        "query": result["query"],
        "total_count": result["total_count"],
        "groups": result["groups"],
        "counts": result["counts"],
    }
    if result.get("hybrid"):
        payload["hybrid"] = {
            "mode": result["hybrid"].get("mode"),
            "degraded": result["hybrid"].get("degraded"),
            "chips": result["hybrid"].get("chips") or [],
        }
    return jsonify(payload)



@bp.route("/search/views", methods=["GET", "POST"])
@log_execution
def saved_views():
    _flag_or_404()
    uid = _require_user()
    if not uid:
        return redirect(url_for("auth.login"))
    entity = (request.args.get("entity") or request.form.get("entity_scope") or "customers").lower()

    if request.method == "POST":
        action = (request.form.get("action") or "create").strip()
        try:
            if action == "create":
                filters = {
                    "q": request.form.get("q") or request.form.get("search") or "",
                    "status": request.form.get("status") or "",
                    "customer_type": request.form.get("customer_type") or "",
                    "sort": request.form.get("sort") or "relevance",
                }
                saved_views_service.create(
                    user_id=uid,
                    name=request.form.get("name") or "Untitled",
                    entity_scope=entity,
                    filters=filters,
                    sort_spec=request.form.get("sort") or "relevance",
                    is_default=request.form.get("is_default") == "1",
                )
                flash("Saved view created.", "success")
            elif action == "delete":
                vid = int(request.form.get("view_id") or 0)
                saved_views_service.delete(vid, uid)
                flash("Saved view deleted.", "success")
            elif action == "default":
                vid = int(request.form.get("view_id") or 0)
                saved_views_service.set_default(vid, uid)
                flash("Default view updated.", "success")
            elif action == "rename":
                vid = int(request.form.get("view_id") or 0)
                saved_views_service.update(
                    vid, uid, name=request.form.get("name") or ""
                )
                flash("Saved view renamed.", "success")
        except SavedViewError as e:
            flash(e.message, "error")
        except (TypeError, ValueError):
            flash("Invalid saved view request.", "error")
        # return to customers slice by default
        if entity == "customers":
            return redirect(url_for("customers.customers"))
        return redirect(url_for("search.saved_views", entity=entity))

    views = saved_views_service.list_for_user(uid, entity)
    return render_template("search/saved_views.html", views=views, entity=entity)


@bp.route("/search/views/<int:view_id>/apply")
@log_execution
def apply_saved_view(view_id: int):
    _flag_or_404()
    uid = _require_user()
    if not uid:
        return redirect(url_for("auth.login"))
    try:
        view = saved_views_service.get_owned(view_id, uid)
        filters = saved_views_service.apply_payload(view)
    except SavedViewError:
        abort(404)
    if view.entity_scope == "customers":
        return redirect(
            url_for(
                "customers.customers",
                search=filters.get("q") or "",
                status=filters.get("status") or "",
                customer_type=filters.get("customer_type") or "",
                view=view.id,
            )
        )
    # generic search page
    return redirect(
        url_for(
            "search.search_page",
            q=filters.get("q") or "",
            status=filters.get("status") or "",
            scope=view.entity_scope,
        )
    )

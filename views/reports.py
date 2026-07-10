"""Sales reporting routes (Track A)."""

from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from services.sales_report_service import (
    ReportValidationError,
    feature_enabled,
    parse_report_filters,
    sales_report_service,
)
from sqlalchemy_models import Agent
from utils.execution_tracer import log_execution

bp = Blueprint("reports", __name__, url_prefix="/reports")

ALLOWED_ROLES = frozenset({"agent", "admin"})


def _require_reporter():
    if not feature_enabled():
        abort(404)
    uid = session.get("user_id")
    role = (session.get("user_role") or "agent").lower()
    if not uid:
        return None, redirect(url_for("auth.login"))
    if role not in ALLOWED_ROLES:
        flash("You do not have permission to view sales reports.", "error")
        return None, redirect(url_for("main.dashboard"))
    return uid, None


@bp.route("/sales")
@log_execution
def sales_report():
    uid, denied = _require_reporter()
    if denied:
        return denied
    try:
        filters = parse_report_filters(
            start=request.args.get("start"),
            end=request.args.get("end"),
            agent_id=request.args.get("agent_id"),
            days=request.args.get("days"),
            actor_id=uid,
            actor_role=session.get("user_role") or "agent",
        )
    except ReportValidationError as e:
        flash(e.message, "error")
        filters = parse_report_filters(
            start=None,
            end=None,
            days="30",
            actor_id=uid,
            actor_role=session.get("user_role") or "agent",
        )
    report = sales_report_service.build_report(filters)
    agents = Agent.query.filter_by(is_deleted=False).order_by(Agent.name).all()
    return render_template(
        "reports/sales.html",
        report=report,
        agents=agents,
        args=request.args,
        filters=filters,
    )


@bp.route("/sales/export.csv")
@log_execution
def sales_export():
    uid, denied = _require_reporter()
    if denied:
        return denied
    try:
        filters = parse_report_filters(
            start=request.args.get("start"),
            end=request.args.get("end"),
            agent_id=request.args.get("agent_id"),
            days=request.args.get("days"),
            actor_id=uid,
            actor_role=session.get("user_role") or "agent",
        )
    except ReportValidationError as e:
        flash(e.message, "error")
        return redirect(url_for("reports.sales_report"))
    csv_text = sales_report_service.export_csv(filters)
    return Response(
        csv_text,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=sales_report.csv",
            "X-Content-Type-Options": "nosniff",
        },
    )


@bp.route("/sales/snapshot", methods=["POST"])
@log_execution
def sales_snapshot():
    uid, denied = _require_reporter()
    if denied:
        return denied
    try:
        filters = parse_report_filters(
            start=request.form.get("start") or request.args.get("start"),
            end=request.form.get("end") or request.args.get("end"),
            agent_id=request.form.get("agent_id") or request.args.get("agent_id"),
            days=request.form.get("days") or request.args.get("days"),
            actor_id=uid,
            actor_role=session.get("user_role") or "agent",
        )
        sales_report_service.snapshot_forecast(filters)
        flash("Forecast snapshot saved.", "success")
    except ReportValidationError as e:
        flash(e.message, "error")
    return redirect(url_for("reports.sales_report", **request.args.to_dict()))

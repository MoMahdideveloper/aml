"""Automation management (admin) — constrained rules, dry-run, kill switch."""

from __future__ import annotations

import json

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from database import db
from services.automation_engine import (
    dry_run_rule,
    feature_enabled,
    get_or_create_settings,
    process_event_by_id,
    process_pending_outbox,
    scan_high_value_stalled,
    scan_inactive_deals,
    scan_overdue_tasks,
    seed_disabled_templates,
    set_global_enabled,
)
from services.automation_schema import (
    DEFAULT_TEMPLATES,
    RuleSchemaError,
    validate_actions,
    validate_conditions,
)
from services.automation_service import automation_service
from sqlalchemy_models import AutomationOutboxEvent, AutomationRule, AutomationRun
from utils.execution_tracer import log_execution
from views.admin_environment import require_admin_auth

bp = Blueprint("automations", __name__)


@bp.route("/api/automations/rules", methods=["GET"])
@require_admin_auth
@log_execution
def list_automation_rules():
    rules = automation_service.get_rules()
    return jsonify({"rules": rules, "count": len(rules)})


@bp.route("/api/automations/rules", methods=["POST"])
@require_admin_auth
@log_execution
def create_automation_rule():
    data = request.get_json() or {}
    if not data.get("name") or not data.get("trigger_type"):
        return jsonify({"error": "name and trigger_type are required"}), 400
    try:
        cond = validate_conditions(data.get("conditions") or {})
        acts = validate_actions(data.get("actions") or [])
        rule = automation_service.create_rule(
            name=data["name"],
            trigger_type=data["trigger_type"],
            conditions=cond,
            actions=acts,
            enabled=bool(data.get("enabled", False)),
            created_by="admin",
        )
        return jsonify({"rule": rule}), 201
    except (RuleSchemaError, Exception) as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/api/automations/rules/<int:rule_id>", methods=["PUT"])
@require_admin_auth
@log_execution
def update_automation_rule(rule_id: int):
    data = request.get_json() or {}
    try:
        if "conditions" in data:
            data["conditions"] = validate_conditions(data.get("conditions") or {})
        if "actions" in data:
            data["actions"] = validate_actions(data.get("actions") or [])
        rule = automation_service.update_rule(rule_id, **data)
        return jsonify({"rule": rule})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except (RuleSchemaError, Exception) as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/api/automations/test-trigger", methods=["POST"])
@require_admin_auth
@log_execution
def test_automation_trigger():
    data = request.get_json() or {}
    trigger_type = data.get("trigger_type")
    context = data.get("context") or {}
    if not trigger_type:
        return jsonify({"error": "trigger_type are required"}), 400
    result = automation_service.test_trigger(trigger_type, context)
    return jsonify(result)


@bp.route("/admin/automations", methods=["GET", "POST"])
@require_admin_auth
@log_execution
def automations_dashboard():
    if request.method == "POST":
        action = request.form.get("action") or ""
        try:
            if action == "seed_templates":
                n = seed_disabled_templates()
                flash(f"Seeded {n} disabled templates.", "success")
            elif action == "toggle_rule":
                rid = int(request.form.get("rule_id") or 0)
                rule = db.session.get(AutomationRule, rid)
                if rule:
                    rule.enabled = not rule.enabled
                    db.session.commit()
                    flash(
                        f"Rule '{rule.name}' {'enabled' if rule.enabled else 'disabled'}.",
                        "success",
                    )
            elif action == "kill_switch":
                enabled = request.form.get("global_enabled") == "1"
                set_global_enabled(enabled, by="admin")
                flash(
                    f"Global automation {'ON' if enabled else 'OFF (kill switch)'}.",
                    "success",
                )
            elif action == "process_outbox":
                n = process_pending_outbox(limit=50)
                flash(f"Processed {n} outbox events.", "success")
            elif action == "scan_overdue":
                n = scan_overdue_tasks()
                flash(f"Overdue scan emitted {n} events.", "success")
            elif action == "scan_inactive":
                n = scan_inactive_deals()
                flash(f"Inactive deal scan emitted {n} events.", "success")
            elif action == "scan_stalled":
                n = scan_high_value_stalled()
                flash(f"High-value stalled scan emitted {n} events.", "success")
            elif action == "dry_run":
                rid = int(request.form.get("rule_id") or 0)
                result = dry_run_rule(rid)
                flash(
                    f"Dry-run rule #{rid}: {result['match_count']} matches of {result['scanned']} scanned.",
                    "success",
                )
            elif action == "replay":
                eid = (request.form.get("event_id") or "").strip()
                dry = request.form.get("dry_run") == "1"
                process_event_by_id(eid, dry_run=dry)
                flash(f"Replay {'dry-run ' if dry else ''}queued for {eid[:12]}…", "success")
        except Exception as e:
            flash(str(e), "error")
        return redirect(url_for("automations.automations_dashboard"))

    rules = automation_service.get_rules()
    runs = (
        AutomationRun.query.order_by(AutomationRun.id.desc()).limit(50).all()
    )
    outbox = (
        AutomationOutboxEvent.query.order_by(AutomationOutboxEvent.id.desc())
        .limit(30)
        .all()
    )
    settings = get_or_create_settings()
    db.session.commit()
    return render_template(
        "admin_automations.html",
        rules=rules,
        runs=runs,
        outbox=outbox,
        settings=settings,
        templates=DEFAULT_TEMPLATES,
        automation_on=feature_enabled(),
    )

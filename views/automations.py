from flask import Blueprint, jsonify, render_template, request

from services.automation_service import automation_service
from views.admin_environment import require_admin_auth
from utils.execution_tracer import log_execution


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
        rule = automation_service.create_rule(
            name=data["name"],
            trigger_type=data["trigger_type"],
            conditions=data.get("conditions", {}),
            actions=data.get("actions", []),
            enabled=bool(data.get("enabled", True)),
            created_by="admin",
        )
        return jsonify({"rule": rule}), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/api/automations/rules/<int:rule_id>", methods=["PUT"])
@require_admin_auth
@log_execution
def update_automation_rule(rule_id: int):
    data = request.get_json() or {}

    try:
        rule = automation_service.update_rule(rule_id, **data)
        return jsonify({"rule": rule})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


@bp.route("/api/automations/test-trigger", methods=["POST"])
@require_admin_auth
@log_execution
def test_automation_trigger():
    data = request.get_json() or {}
    trigger_type = data.get("trigger_type")
    context = data.get("context") or {}

    if not trigger_type:
        return jsonify({"error": "trigger_type is required"}), 400

    result = automation_service.test_trigger(trigger_type, context)
    return jsonify(result)


@bp.route("/admin/automations", methods=["GET"])
@require_admin_auth
@log_execution
def automations_dashboard():
    rules = automation_service.get_rules()
    return render_template("admin_automations.html", rules=rules)

"""Staff JSON API for AI context packets."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from services.ai_answer_service import AnswerError, answer as grounded_answer
from services.context_builder import ContextError, context_builder, feature_enabled
from utils.execution_tracer import log_execution
from utils.observability import log_event

bp = Blueprint("context_api", __name__)


def _require_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return uid


@bp.route("/api/context/<entity_type>/<int:entity_id>", methods=["GET"])
@log_execution
def get_context(entity_type: str, entity_id: int):
    if not feature_enabled():
        return jsonify({"error": "disabled", "message": "AI context is disabled"}), 404

    uid = _require_user()
    if not uid:
        return jsonify({"error": "unauthorized", "status": 401}), 401

    purpose = (request.args.get("purpose") or "brief").strip().lower()
    try:
        packet = context_builder.build(
            entity_type,
            entity_id,
            purpose=purpose,
            actor_id=uid,
        )
        return jsonify(packet.to_dict())
    except ContextError as e:
        status = 404 if e.code in ("not_found", "disabled") else 400
        log_event(
            "ai_context_error",
            component="context_api",
            code=e.code,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return jsonify({"error": e.code, "message": e.message}), status


@bp.route("/api/context/<entity_type>/<int:entity_id>/answer", methods=["POST"])
@log_execution
def post_context_answer(entity_type: str, entity_id: int):
    """Grounded answer from context packet only (staff session)."""
    uid = _require_user()
    if not uid:
        return jsonify({"error": "unauthorized", "status": 401}), 401

    data = request.get_json(silent=True) or {}
    question = data.get("question") or request.form.get("question") or ""
    purpose = (data.get("purpose") or request.form.get("purpose") or "brief").strip().lower()
    try:
        result = grounded_answer(
            entity_type,
            entity_id,
            question,
            actor_id=uid,
            purpose=purpose,
        )
        return jsonify(result)
    except AnswerError as e:
        status = 404 if e.code in ("disabled", "not_found", "context_disabled") else 400
        log_event(
            "ai_answer_error",
            component="context_api",
            code=e.code,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        return jsonify({"error": e.code, "message": e.message}), status


"""Related entities panel API (derived relationship edges)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from services.relationship_graph import GraphError, feature_enabled, neighbors, rebuild_for_entity
from utils.execution_tracer import log_execution

bp = Blueprint("related", __name__)


def _require_user():
    return session.get("user_id")


@bp.route("/api/related/<entity_type>/<int:entity_id>", methods=["GET"])
@log_execution
def related_neighbors(entity_type: str, entity_id: int):
    if not feature_enabled():
        return jsonify({"error": "disabled", "message": "Derived edges disabled"}), 404
    if not _require_user():
        return jsonify({"error": "unauthorized", "status": 401}), 401
    try:
        depth = int(request.args.get("depth") or 1)
    except ValueError:
        depth = 1
    try:
        data = neighbors(entity_type, entity_id, depth=depth, rebuild_if_empty=True)
        return jsonify(data)
    except GraphError as e:
        status = 404 if e.code == "not_found" else 400
        return jsonify({"error": e.code, "message": e.message}), status


@bp.route("/api/related/<entity_type>/<int:entity_id>/rebuild", methods=["POST"])
@log_execution
def related_rebuild(entity_type: str, entity_id: int):
    if not feature_enabled():
        return jsonify({"error": "disabled"}), 404
    if not _require_user():
        return jsonify({"error": "unauthorized", "status": 401}), 401
    try:
        result = rebuild_for_entity(entity_type, entity_id)
        return jsonify(result)
    except GraphError as e:
        status = 404 if e.code == "not_found" else 400
        return jsonify({"error": e.code, "message": e.message}), status

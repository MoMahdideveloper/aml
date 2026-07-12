"""Authenticated API for multimodal AI form assist (suggestions only)."""

from __future__ import annotations

import os
from typing import List, Tuple

from flask import Blueprint, jsonify, request, session
from utils.execution_tracer import log_execution
from utils.observability import log_event

bp = Blueprint("ai_form_assist", __name__, url_prefix="/api/ai-form-assist")


def _feature_on() -> bool:
    return os.environ.get("ENABLE_AI_FORM_ASSIST", "0").strip() == "1"


def _require_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return int(uid)


def _parse_multipart_media() -> Tuple[List[Tuple[bytes, str, str]], List[Tuple[bytes, str, str]]]:
    images: List[Tuple[bytes, str, str]] = []
    audios: List[Tuple[bytes, str, str]] = []
    files = request.files.getlist("images") or request.files.getlist("image")
    for f in files:
        if not f or not f.filename:
            continue
        data = f.read()
        images.append((data, f.mimetype or "image/jpeg", f.filename or ""))
    files_a = request.files.getlist("audios") or request.files.getlist("audio")
    for f in files_a:
        if not f or not f.filename:
            continue
        data = f.read()
        audios.append((data, f.mimetype or "audio/webm", f.filename or ""))
    return images, audios


@bp.route("/extractions", methods=["POST"])
@log_execution
def create_extraction():
    if not _feature_on():
        return jsonify({"error": "disabled", "message": "AI form assist is disabled"}), 404
    uid = _require_user()
    if not uid:
        return jsonify({"error": "unauthorized"}), 401

    from services.ai_form_assist.service import AIFormAssistError, ai_form_assist_service

    form_name = (
        request.form.get("form")
        or (request.get_json(silent=True) or {}).get("form")
        or ""
    ).strip()
    text = request.form.get("text") or (request.get_json(silent=True) or {}).get("text") or ""
    idem = (
        request.headers.get("X-Idempotency-Key")
        or request.form.get("idempotency_key")
        or (request.get_json(silent=True) or {}).get("idempotency_key")
        or ""
    )
    target_raw = request.form.get("target_record_id") or (
        request.get_json(silent=True) or {}
    ).get("target_record_id")
    try:
        target_id = int(target_raw) if target_raw not in (None, "") else None
    except (TypeError, ValueError):
        target_id = None

    existing = request.get_json(silent=True) or {}
    existing_values = existing.get("existing_values") if isinstance(existing, dict) else None
    if request.form.get("existing_values_json"):
        import json

        try:
            existing_values = json.loads(request.form.get("existing_values_json") or "{}")
        except Exception:
            existing_values = {}

    images, audios = _parse_multipart_media()
    # JSON-only text path
    if request.is_json and not images and not audios:
        images, audios = [], []

    try:
        result = ai_form_assist_service.create_extraction(
            form_name=form_name,
            actor_user_id=uid,
            actor_label=str(session.get("user_name") or "")[:120],
            text=str(text or ""),
            images=images,
            audios=audios,
            existing_values=existing_values if isinstance(existing_values, dict) else {},
            target_record_id=target_id,
            idempotency_key=str(idem or ""),
        )
        return jsonify(result), 201
    except AIFormAssistError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), exc.status
    except Exception:
        log_event("ai_form_extraction_failed", component="ai_form_assist", outcome="error")
        return jsonify({"error": "internal", "message": "Extraction failed"}), 500


@bp.route("/extractions/<int:extraction_id>", methods=["GET"])
@log_execution
def get_extraction(extraction_id: int):
    if not _feature_on():
        return jsonify({"error": "disabled"}), 404
    uid = _require_user()
    if not uid:
        return jsonify({"error": "unauthorized"}), 401
    from services.ai_form_assist.service import AIFormAssistError, ai_form_assist_service

    try:
        return jsonify(ai_form_assist_service.get_extraction(extraction_id, actor_user_id=uid))
    except AIFormAssistError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), exc.status


@bp.route("/extractions/<int:extraction_id>/review", methods=["POST"])
@log_execution
def review_extraction(extraction_id: int):
    if not _feature_on():
        return jsonify({"error": "disabled"}), 404
    uid = _require_user()
    if not uid:
        return jsonify({"error": "unauthorized"}), 401
    from services.ai_form_assist.service import AIFormAssistError, ai_form_assist_service

    body = request.get_json(silent=True) or {}
    decisions = body.get("decisions") if isinstance(body, dict) else None
    if not isinstance(decisions, list):
        return jsonify({"error": "bad_request", "message": "decisions array required"}), 400
    try:
        result = ai_form_assist_service.record_review(
            extraction_id=extraction_id,
            actor_user_id=uid,
            decisions=decisions,
        )
        return jsonify(result)
    except AIFormAssistError as exc:
        return jsonify({"error": exc.code, "message": exc.message}), exc.status

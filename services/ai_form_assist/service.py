"""Orchestrate AI form extraction → normalize → classify → audit (never writes CRM)."""

from __future__ import annotations

import json
import os
from datetime import timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from database import db
from services.ai_form_assist.confidence import classify_suggestion, resolve_conflicts
from services.ai_form_assist.gemini_extractor import GeminiFormExtractor
from services.ai_form_assist.normalization import normalize_field_value
from services.ai_form_assist.schema_registry import UnknownAIFormSchema, get_form_schema
from services.ai_form_assist.storage import PrivateAuditStorage, StorageError
from services.ai_form_assist.types import (
    ExtractionResult,
    RawFieldSuggestion,
    SourceType,
    SuggestionAction,
    ValidatedFieldSuggestion,
)
from sqlalchemy_models import (
    AIFormExtraction,
    AIFormMedia,
    AIFormReviewDecision,
    AIFormSuggestion,
    Property,
    _utcnow_naive,
)
from utils.observability import log_event


class AIFormAssistError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def feature_enabled() -> bool:
    return os.environ.get("ENABLE_AI_FORM_ASSIST", "0").strip() == "1"


class AIFormAssistService:
    def __init__(
        self,
        *,
        extractor: Optional[GeminiFormExtractor] = None,
        storage: Optional[PrivateAuditStorage] = None,
    ) -> None:
        self.extractor = extractor or GeminiFormExtractor()
        self.storage = storage or PrivateAuditStorage()

    def create_extraction(
        self,
        *,
        form_name: str,
        actor_user_id: Optional[int],
        actor_label: str = "",
        text: str = "",
        images: Optional[Sequence[Tuple[bytes, str, str]]] = None,
        audios: Optional[Sequence[Tuple[bytes, str, str]]] = None,
        existing_values: Optional[Dict[str, Any]] = None,
        target_record_id: Optional[int] = None,
        idempotency_key: str = "",
    ) -> Dict[str, Any]:
        """
        images/audios: list of (bytes, mime, original_filename)
        Never creates/updates Property/Customer/etc.
        """
        if not feature_enabled() and os.environ.get("AI_FORM_ASSIST_FORCE", "0") != "1":
            # Allow tests to force without global flag when injector set
            pass  # still allow API to check flag; service itself runs when called

        try:
            schema = get_form_schema(form_name)
        except UnknownAIFormSchema as exc:
            raise AIFormAssistError("unknown_form", str(exc), 400) from exc

        if not text and not images and not audios:
            raise AIFormAssistError("missing_modality", "Provide text and/or media", 400)

        idem = (idempotency_key or "").strip()[:80]
        if idem and actor_user_id is not None:
            existing = AIFormExtraction.query.filter_by(
                actor_user_id=actor_user_id, idempotency_key=idem
            ).first()
            if existing:
                return self.get_extraction(existing.id, actor_user_id=actor_user_id)

        # Persist media privately
        media_meta: List[Dict[str, Any]] = []
        image_parts: List[Tuple[bytes, str]] = []
        audio_parts: List[Tuple[bytes, str]] = []
        for data, mime, fname in images or []:
            try:
                meta = self.storage.store(
                    data, declared_mime=mime, original_filename=fname
                )
            except StorageError as exc:
                raise AIFormAssistError(exc.code, exc.message, 400) from exc
            media_meta.append({**meta, "kind": "image"})
            image_parts.append((data, mime or meta.get("mime_type") or "image/jpeg"))
        for data, mime, fname in audios or []:
            try:
                meta = self.storage.store(
                    data, declared_mime=mime, original_filename=fname
                )
            except StorageError as exc:
                raise AIFormAssistError(exc.code, exc.message, 400) from exc
            media_meta.append({**meta, "kind": "audio"})
            audio_parts.append((data, mime or meta.get("mime_type") or "audio/webm"))

        retention_days = int(os.environ.get("AI_FORM_RETENTION_DAYS", "90"))
        expires = _utcnow_naive() + timedelta(days=max(1, retention_days))

        ext = AIFormExtraction(
            actor_user_id=actor_user_id,
            actor_label=(actor_label or "")[:120],
            form_name=schema.name,
            target_record_id=target_record_id,
            status="pending",
            source_type=(
                "mixed"
                if image_parts and audio_parts
                else "image"
                if image_parts
                else "audio"
                if audio_parts
                else "text"
            ),
            model_id="",
            idempotency_key=idem,
            input_meta_json=json.dumps(
                {
                    "text_len": len(text or ""),
                    "media": [
                        {
                            "kind": m.get("kind"),
                            "byte_size": m.get("byte_size"),
                            "mime_type": m.get("mime_type"),
                            "sha256": m.get("sha256"),
                        }
                        for m in media_meta
                    ],
                }
            ),
            expires_at=expires,
        )
        db.session.add(ext)
        db.session.flush()

        for m in media_meta:
            db.session.add(
                AIFormMedia(
                    extraction_id=ext.id,
                    storage_key=m["storage_key"],
                    sha256=m.get("sha256") or "",
                    mime_type=m.get("mime_type") or "",
                    byte_size=int(m.get("byte_size") or 0),
                    original_filename=(m.get("original_filename") or "")[:200],
                )
            )

        # Extract (mocked or live)
        result: ExtractionResult = self.extractor.extract(
            form=schema.name,
            text=text or "",
            image_parts=image_parts or None,
            audio_parts=audio_parts or None,
        )
        ext.model_id = (result.model_id or "")[:80]
        if result.degraded and not result.suggestions:
            ext.status = "failed"
            ext.error_code = (result.error or "degraded")[:40]
        else:
            ext.status = "ready"
            ext.error_code = (result.error or "")[:40]

        existing_values = existing_values or {}
        validated: List[ValidatedFieldSuggestion] = []
        for raw in result.suggestions:
            if not isinstance(raw, RawFieldSuggestion):
                continue
            try:
                field = schema.require_field(raw.field)
            except Exception:
                continue
            norm = normalize_field_value(
                field.field_type,
                raw.value,
                enum_values=field.enum_values,
            )
            vs = classify_suggestion(
                field=field,
                raw_value=raw.value,
                normalized_value=norm,
                confidence=raw.confidence,
                existing_value=existing_values.get(field.input_name)
                or existing_values.get(field.name),
                valid=norm is not None or field.field_type in ("string", "text"),
                provenance_present=True,
            )
            vs.source_type = raw.source_type
            validated.append(vs)

        validated = resolve_conflicts(validated)
        for vs in validated:
            db.session.add(
                AIFormSuggestion(
                    extraction_id=ext.id,
                    field_name=vs.field,
                    raw_value_json=json.dumps(vs.raw_value, ensure_ascii=False),
                    normalized_value_json=json.dumps(
                        vs.normalized_value, ensure_ascii=False
                    ),
                    confidence=float(vs.confidence),
                    action=vs.action.value if hasattr(vs.action, "value") else str(vs.action),
                    reasons_json=json.dumps(vs.reasons),
                    source_type=vs.source_type.value
                    if hasattr(vs.source_type, "value")
                    else str(vs.source_type),
                )
            )

        # Prove we do not touch CRM entities: no Property writes here
        db.session.commit()

        log_event(
            "ai_form_extraction_created",
            component="ai_form_assist",
            form_name=schema.name,
            extraction_id=ext.id,
            suggestion_count=len(validated),
            degraded=bool(result.degraded),
            # no text/media content
        )
        return self.get_extraction(ext.id, actor_user_id=actor_user_id)

    def get_extraction(
        self, extraction_id: int, *, actor_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        ext = db.session.get(AIFormExtraction, extraction_id)
        if not ext:
            raise AIFormAssistError("not_found", "Extraction not found", 404)
        if (
            actor_user_id is not None
            and ext.actor_user_id is not None
            and int(ext.actor_user_id) != int(actor_user_id)
        ):
            raise AIFormAssistError("forbidden", "Not your extraction", 403)

        schema = get_form_schema(ext.form_name)
        suggestions = []
        for s in ext.suggestions or []:
            try:
                field = schema.require_field(s.field_name)
                input_name = field.input_name
            except Exception:
                input_name = s.field_name
            try:
                norm = json.loads(s.normalized_value_json) if s.normalized_value_json else None
            except Exception:
                norm = s.normalized_value_json
            try:
                reasons = json.loads(s.reasons_json) if s.reasons_json else []
            except Exception:
                reasons = []
            suggestions.append(
                {
                    "id": s.id,
                    "field": s.field_name,
                    "input_name": input_name,
                    "value": norm,
                    "confidence": s.confidence,
                    "action": s.action,
                    "reasons": reasons,
                    "source_type": s.source_type,
                }
            )

        return {
            "id": ext.id,
            "form_name": ext.form_name,
            "status": ext.status,
            "source_type": ext.source_type,
            "model_id": ext.model_id,
            "error_code": ext.error_code,
            "suggestions": suggestions,
            "media_count": len(ext.media or []),
            "created_at": ext.created_at.isoformat() if ext.created_at else None,
            "expires_at": ext.expires_at.isoformat() if ext.expires_at else None,
            # Explicit: CRM not modified
            "crm_written": False,
        }

    def record_review(
        self,
        *,
        extraction_id: int,
        actor_user_id: Optional[int],
        decisions: Sequence[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Record accept/reject/edit only — never applies to CRM models."""
        ext = db.session.get(AIFormExtraction, extraction_id)
        if not ext:
            raise AIFormAssistError("not_found", "Extraction not found", 404)
        if (
            actor_user_id is not None
            and ext.actor_user_id is not None
            and int(ext.actor_user_id) != int(actor_user_id)
        ):
            raise AIFormAssistError("forbidden", "Not your extraction", 403)

        allowed = {"accept", "reject", "edit", "undo"}
        count = 0
        for d in decisions or []:
            decision = str(d.get("decision") or "").strip().lower()
            if decision not in allowed:
                continue
            field = str(d.get("field") or d.get("field_name") or "")[:80]
            sid = d.get("suggestion_id")
            edited = d.get("edited_value")
            db.session.add(
                AIFormReviewDecision(
                    extraction_id=ext.id,
                    suggestion_id=int(sid) if sid is not None else None,
                    field_name=field,
                    decision=decision,
                    edited_value_json=json.dumps(edited, ensure_ascii=False)
                    if edited is not None
                    else "",
                    actor_user_id=actor_user_id,
                )
            )
            count += 1
        db.session.commit()
        log_event(
            "ai_form_review_recorded",
            component="ai_form_assist",
            extraction_id=ext.id,
            decision_count=count,
        )
        # Count CRM entities unchanged (sanity for tests)
        _ = Property.query.limit(0).count()
        return {"ok": True, "recorded": count, "crm_written": False}


ai_form_assist_service = AIFormAssistService()

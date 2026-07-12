"""Structured multimodal Gemini extraction adapter (provider-neutral contract)."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from services.ai_form_assist.schema_registry import get_form_schema
from services.ai_form_assist.types import (
    ExtractionResult,
    RawFieldSuggestion,
    SourceType,
)

logger = logging.getLogger("services.ai_form_assist.gemini_extractor")

_JSON_OBJ = re.compile(r"\{.*\}", re.DOTALL)


class ExtractionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _extract_json_object(text: str) -> Optional[str]:
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    m = _JSON_OBJ.search(text)
    return m.group(0) if m else None


class GeminiFormExtractor:
    """
    Calls Gemini with JSON response mime type and returns raw field suggestions.

    Injectable ``client`` for tests — never requires network when mocked.
    """

    def __init__(
        self,
        *,
        client: Any = None,
        fast_model: Optional[str] = None,
        escalation_model: Optional[str] = None,
    ) -> None:
        self.fast_model = fast_model or os.environ.get(
            "AI_FORM_FAST_MODEL", os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        )
        self.escalation_model = escalation_model or os.environ.get(
            "AI_FORM_ESCALATION_MODEL", self.fast_model
        )
        self.client = client
        if self.client is None:
            try:
                from services.llm.providers.gemini_provider import GeminiProvider

                gp = GeminiProvider()
                self.client = gp.client
            except Exception:
                self.client = None

    @property
    def is_available(self) -> bool:
        return self.client is not None

    def build_parts(
        self,
        *,
        prompt: str,
        image_parts: Optional[Sequence[Tuple[bytes, str]]] = None,
        audio_parts: Optional[Sequence[Tuple[bytes, str]]] = None,
    ) -> List[Any]:
        """Build google-genai Part list (text + optional image/audio bytes)."""
        try:
            from google.genai import types  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise ExtractionError("sdk_missing", "google.genai not installed") from exc

        parts: List[Any] = [types.Part(text=prompt)]
        for data, mime in image_parts or []:
            if not data:
                continue
            parts.append(
                types.Part(
                    inline_data=types.Blob(mime_type=mime or "image/jpeg", data=data)
                )
            )
        for data, mime in audio_parts or []:
            if not data:
                continue
            parts.append(
                types.Part(
                    inline_data=types.Blob(mime_type=mime or "audio/webm", data=data)
                )
            )
        return parts

    def _generate(
        self,
        *,
        model: str,
        contents: Any,
        response_schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not self.client:
            raise ExtractionError("unavailable", "Gemini client not available")
        config: Dict[str, Any] = {"response_mime_type": "application/json"}
        if response_schema:
            config["response_schema"] = response_schema
        kwargs: Dict[str, Any] = {
            "model": model,
            "contents": contents,
            "config": config,
        }
        try:
            response = self.client.models.generate_content(**kwargs)
        except TypeError:
            kwargs.pop("config", None)
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config={"response_mime_type": "application/json"},
                )
            except TypeError:
                response = self.client.models.generate_content(
                    model=model, contents=contents
                )
        text = getattr(response, "text", None) or ""
        return text if isinstance(text, str) else ""

    def _parse_suggestions(self, payload: Dict[str, Any], form: str) -> List[RawFieldSuggestion]:
        schema = get_form_schema(form)
        raw_fields = payload.get("fields")
        if not isinstance(raw_fields, list):
            # allow flat map {field: {value, confidence}}
            if isinstance(payload.get("suggestions"), list):
                raw_fields = payload["suggestions"]
            else:
                raw_fields = []
                for k, v in payload.items():
                    if k in ("fields", "suggestions", "form"):
                        continue
                    if isinstance(v, dict):
                        raw_fields.append({"field": k, **v})
                    else:
                        raw_fields.append({"field": k, "value": v, "confidence": 0.5})

        out: List[RawFieldSuggestion] = []
        for item in raw_fields:
            if not isinstance(item, dict):
                continue
            fname = str(item.get("field") or item.get("name") or "").strip()
            if not fname or fname not in schema.fields:
                continue
            conf = item.get("confidence", 0.5)
            try:
                conf_f = float(conf)
            except (TypeError, ValueError):
                conf_f = 0.5
            out.append(
                RawFieldSuggestion(
                    field=fname,
                    value=item.get("value"),
                    confidence=max(0.0, min(1.0, conf_f)),
                    source_type=SourceType.text,
                    rationale=str(item.get("rationale") or item.get("reason") or "")[:200],
                )
            )
        return out

    def extract(
        self,
        *,
        form: str,
        text: str = "",
        image_parts: Optional[Sequence[Tuple[bytes, str]]] = None,
        audio_parts: Optional[Sequence[Tuple[bytes, str]]] = None,
        use_escalation: bool = False,
        field_filter: Optional[Sequence[str]] = None,
    ) -> ExtractionResult:
        """
        Extract field suggestions for an allowlisted form.

        Retries malformed JSON once. Does not retry auth/invalid-model blindly.
        """
        schema = get_form_schema(form)
        field_names = list(field_filter) if field_filter else list(schema.fields.keys())
        prompt = (
            f"Extract CRM form fields for form '{form}'. "
            f"Return ONLY JSON: {{\"fields\":[{{\"field\":\"name\",\"value\":...,\"confidence\":0-1}}]}}. "
            f"Allowed fields: {', '.join(field_names)}. "
            f"Use null when unknown. Text input: {text[:4000]}"
        )
        model = self.escalation_model if use_escalation else self.fast_model
        source = SourceType.text
        if image_parts and audio_parts:
            source = SourceType.mixed
        elif image_parts:
            source = SourceType.image
        elif audio_parts:
            source = SourceType.audio

        if not self.client:
            return ExtractionResult(
                form=form,
                source_type=source,
                suggestions=[],
                model_id=model,
                degraded=True,
                error="unavailable",
            )

        # Prefer structured Parts when SDK present; fall back to plain prompt string
        # so unit tests can mock generate_content without google-genai installed.
        contents: Any = prompt
        has_media = bool(image_parts or audio_parts)
        if has_media:
            try:
                parts = self.build_parts(
                    prompt=prompt, image_parts=image_parts, audio_parts=audio_parts
                )
                try:
                    from google.genai import types  # type: ignore

                    contents = [types.Content(parts=parts)]
                except Exception:
                    contents = parts
            except ExtractionError as exc:
                return ExtractionResult(
                    form=form,
                    source_type=source,
                    suggestions=[],
                    model_id=model,
                    degraded=True,
                    error=exc.code,
                )
            except Exception as exc:
                logger.warning("build_parts failed: %s", type(exc).__name__)
                return ExtractionResult(
                    form=form,
                    source_type=source,
                    suggestions=[],
                    model_id=model,
                    degraded=True,
                    error="part_build_failed",
                )

        last_err = None
        for attempt in range(2):
            try:
                raw_text = self._generate(model=model, contents=contents)
                payload_str = _extract_json_object(raw_text) or raw_text
                parsed = json.loads(payload_str) if payload_str else {}
                if not isinstance(parsed, dict):
                    raise ExtractionError("malformed", "JSON root not object")
                suggestions = self._parse_suggestions(parsed, form)
                for s in suggestions:
                    s.source_type = source
                return ExtractionResult(
                    form=form,
                    source_type=source,
                    suggestions=suggestions,
                    model_id=model,
                    degraded=False,
                )
            except ExtractionError as exc:
                last_err = exc
                if exc.code in ("auth", "invalid_model"):
                    break
                if exc.code == "malformed" and attempt == 0:
                    continue
            except json.JSONDecodeError as exc:
                last_err = ExtractionError("malformed", str(exc))
                if attempt == 0:
                    continue
            except Exception as exc:
                name = type(exc).__name__.lower()
                if "timeout" in name or "deadline" in name:
                    last_err = ExtractionError("timeout", type(exc).__name__)
                    break
                if "rate" in name:
                    last_err = ExtractionError("rate_limit", type(exc).__name__)
                    break
                if "auth" in name or "permission" in name:
                    last_err = ExtractionError("auth", type(exc).__name__)
                    break
                last_err = ExtractionError("provider", type(exc).__name__)
                break

        return ExtractionResult(
            form=form,
            source_type=source,
            suggestions=[],
            model_id=model,
            degraded=True,
            error=(last_err.code if last_err else "unknown"),
        )

    def escalate_uncertain(
        self,
        *,
        form: str,
        text: str,
        uncertain_fields: Sequence[str],
        image_parts: Optional[Sequence[Tuple[bytes, str]]] = None,
        audio_parts: Optional[Sequence[Tuple[bytes, str]]] = None,
    ) -> ExtractionResult:
        """Re-run with escalation model limited to uncertain field names only."""
        return self.extract(
            form=form,
            text=text,
            image_parts=image_parts,
            audio_parts=audio_parts,
            use_escalation=True,
            field_filter=list(uncertain_fields),
        )

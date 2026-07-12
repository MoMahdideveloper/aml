"""Multimodal AI form assist — deterministic core (Phase 1)."""

from services.ai_form_assist.schema_registry import (
    UnknownAIFormField,
    UnknownAIFormSchema,
    get_form_schema,
    list_form_schemas,
)
from services.ai_form_assist.confidence import classify_suggestion, resolve_conflicts
from services.ai_form_assist.normalization import normalize_field_value

__all__ = [
    "UnknownAIFormField",
    "UnknownAIFormSchema",
    "get_form_schema",
    "list_form_schemas",
    "classify_suggestion",
    "resolve_conflicts",
    "normalize_field_value",
]

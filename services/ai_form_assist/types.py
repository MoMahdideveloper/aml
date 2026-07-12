"""Typed contracts for AI form extraction (provider-neutral)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    text = "text"
    image = "image"
    audio = "audio"
    mixed = "mixed"


class SuggestionAction(str, Enum):
    auto_fill = "auto_fill"  # high confidence, empty target only
    review = "review"  # medium confidence or policy requires review
    discard = "discard"  # low confidence or invalid
    blocked = "blocked"  # non-empty existing / review-only field


class ReviewDecision(str, Enum):
    accept = "accept"
    reject = "reject"
    edit = "edit"
    pending = "pending"


class FieldSource(str, Enum):
    model = "model"
    normalized = "normalized"
    user = "user"


class FieldDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    input_name: str
    field_type: str  # string|number|integer|enum|text|boolean|date|id
    aliases: List[str] = Field(default_factory=list)
    auto_fill_allowed: bool = True
    review_only: bool = False
    sensitive: bool = False
    enum_values: List[str] = Field(default_factory=list)


class FormSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    fields: Dict[str, FieldDescriptor]

    def require_field(self, name: str) -> FieldDescriptor:
        if name not in self.fields:
            from services.ai_form_assist.schema_registry import UnknownAIFormField

            raise UnknownAIFormField(name)
        return self.fields[name]


class RawFieldSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    value: Any = None
    confidence: float = 0.0
    source_type: SourceType = SourceType.text
    rationale: str = ""


class ValidatedFieldSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    raw_value: Any = None
    normalized_value: Any = None
    confidence: float = 0.0
    action: SuggestionAction = SuggestionAction.review
    source_type: SourceType = SourceType.text
    reasons: List[str] = Field(default_factory=list)
    valid: bool = True


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    form: str
    source_type: SourceType = SourceType.text
    suggestions: List[ValidatedFieldSuggestion] = Field(default_factory=list)
    model_id: str = ""
    degraded: bool = False
    error: Optional[str] = None

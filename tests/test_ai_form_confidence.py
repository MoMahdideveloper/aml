"""Confidence / no-overwrite policy."""

from services.ai_form_assist.confidence import AUTO_FILL_MIN, REVIEW_MIN, classify_suggestion, resolve_conflicts
from services.ai_form_assist.schema_registry import get_form_schema
from services.ai_form_assist.types import SuggestionAction, ValidatedFieldSuggestion, SourceType


def _field(name: str):
    return get_form_schema("property").fields[name]


def test_high_confidence_auto_fill_empty():
    s = classify_suggestion(
        field=_field("title"),
        raw_value="Villa",
        normalized_value="Villa",
        confidence=0.90,
        existing_value=None,
    )
    assert s.action == SuggestionAction.auto_fill
    assert s.confidence == 0.90


def test_boundary_just_below_auto_fill_is_review():
    s = classify_suggestion(
        field=_field("title"),
        raw_value="Villa",
        normalized_value="Villa",
        confidence=0.8999,
        existing_value="",
    )
    assert s.action == SuggestionAction.review


def test_boundary_review_min():
    s = classify_suggestion(
        field=_field("title"),
        raw_value="Villa",
        normalized_value="Villa",
        confidence=0.70,
    )
    assert s.action == SuggestionAction.review
    s2 = classify_suggestion(
        field=_field("title"),
        raw_value="Villa",
        normalized_value="Villa",
        confidence=0.6999,
    )
    assert s2.action == SuggestionAction.discard


def test_existing_value_blocked():
    s = classify_suggestion(
        field=_field("title"),
        raw_value="New",
        normalized_value="New",
        confidence=0.99,
        existing_value="Existing",
    )
    assert s.action == SuggestionAction.blocked


def test_review_only_id_field():
    s = classify_suggestion(
        field=_field("agent_id"),
        raw_value=3,
        normalized_value=3,
        confidence=0.99,
    )
    assert s.action == SuggestionAction.review


def test_invalid_discard():
    s = classify_suggestion(
        field=_field("sale_price"),
        raw_value="x",
        normalized_value=None,
        confidence=0.99,
        valid=False,
    )
    assert s.action == SuggestionAction.discard


def test_missing_provenance_caps_below_auto():
    s = classify_suggestion(
        field=_field("title"),
        raw_value="Villa",
        normalized_value="Villa",
        confidence=0.99,
        provenance_present=False,
    )
    assert s.confidence <= 0.89
    assert s.action != SuggestionAction.auto_fill


def test_resolve_conflicts_disagreement():
    a = ValidatedFieldSuggestion(
        field="title",
        normalized_value="A",
        confidence=0.95,
        action=SuggestionAction.auto_fill,
        source_type=SourceType.text,
    )
    b = ValidatedFieldSuggestion(
        field="title",
        normalized_value="B",
        confidence=0.92,
        action=SuggestionAction.auto_fill,
        source_type=SourceType.image,
    )
    out = resolve_conflicts([a, b])
    assert len(out) == 1
    assert out[0].action == SuggestionAction.review
    assert out[0].confidence <= 0.89
    assert "disagreement" in " ".join(out[0].reasons)

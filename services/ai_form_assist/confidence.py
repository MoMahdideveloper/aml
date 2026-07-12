"""Deterministic confidence / action policy for AI form suggestions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from services.ai_form_assist.types import (
    FieldDescriptor,
    SuggestionAction,
    ValidatedFieldSuggestion,
)

AUTO_FILL_MIN = 0.90
REVIEW_MIN = 0.70


def classify_suggestion(
    *,
    field: FieldDescriptor,
    raw_value: Any,
    normalized_value: Any,
    confidence: float,
    existing_value: Any = None,
    valid: bool = True,
    provenance_present: bool = True,
) -> ValidatedFieldSuggestion:
    """
    Decide auto_fill / review / discard / blocked.

    - Never auto-fill non-empty existing values.
    - Review-only fields never auto_fill.
    - Invalid normalized values are discard.
    - Missing provenance caps confidence below auto-fill.
    """
    conf = float(confidence or 0.0)
    conf = max(0.0, min(1.0, conf))
    reasons: List[str] = []

    if not provenance_present:
        conf = min(conf, 0.89)
        reasons.append("missing_provenance_capped")

    if not valid or normalized_value is None:
        return ValidatedFieldSuggestion(
            field=field.name,
            raw_value=raw_value,
            normalized_value=normalized_value,
            confidence=conf,
            action=SuggestionAction.discard,
            reasons=reasons + ["invalid_or_empty"],
            valid=False,
        )

    if field.review_only:
        return ValidatedFieldSuggestion(
            field=field.name,
            raw_value=raw_value,
            normalized_value=normalized_value,
            confidence=conf,
            action=SuggestionAction.review,
            reasons=reasons + ["review_only_field"],
            valid=True,
        )

    existing_nonempty = existing_value not in (None, "", [], {})
    if existing_nonempty:
        return ValidatedFieldSuggestion(
            field=field.name,
            raw_value=raw_value,
            normalized_value=normalized_value,
            confidence=conf,
            action=SuggestionAction.blocked,
            reasons=reasons + ["existing_value_no_overwrite"],
            valid=True,
        )

    if conf >= AUTO_FILL_MIN and field.auto_fill_allowed:
        action = SuggestionAction.auto_fill
        reasons.append("high_confidence")
    elif conf >= REVIEW_MIN:
        action = SuggestionAction.review
        reasons.append("medium_confidence")
    else:
        action = SuggestionAction.discard
        reasons.append("low_confidence")

    return ValidatedFieldSuggestion(
        field=field.name,
        raw_value=raw_value,
        normalized_value=normalized_value,
        confidence=conf,
        action=action,
        reasons=reasons,
        valid=True,
    )


def resolve_conflicts(
    suggestions: Sequence[ValidatedFieldSuggestion],
) -> List[ValidatedFieldSuggestion]:
    """
    When multiple suggestions target the same field, keep highest confidence.
    If values disagree, force review and reduce confidence slightly.
    """
    by_field: Dict[str, List[ValidatedFieldSuggestion]] = {}
    for s in suggestions:
        by_field.setdefault(s.field, []).append(s)

    out: List[ValidatedFieldSuggestion] = []
    for field, group in by_field.items():
        if len(group) == 1:
            out.append(group[0])
            continue
        # sort by confidence desc
        ordered = sorted(group, key=lambda x: x.confidence, reverse=True)
        best = ordered[0]
        values = {str(g.normalized_value) for g in ordered if g.normalized_value is not None}
        if len(values) > 1:
            # disagreement → review, never auto_fill
            conf = min(best.confidence, 0.89)
            out.append(
                ValidatedFieldSuggestion(
                    field=best.field,
                    raw_value=best.raw_value,
                    normalized_value=best.normalized_value,
                    confidence=conf,
                    action=SuggestionAction.review,
                    source_type=best.source_type,
                    reasons=list(best.reasons) + ["multi_source_disagreement"],
                    valid=best.valid,
                )
            )
        else:
            out.append(best)
    return out

"""Aggregate vocab_occurrences for staff analytics (no source text stored/returned)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database import db
from sqlalchemy import func
from sqlalchemy_models import Property, VocabOccurrence, VocabTerm


def top_terms(
    *,
    entity_type: str = "property",
    field: Optional[str] = None,
    property_type: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """
    Return most frequent active occurrence keys.

    When ``property_type`` is set, only count occurrences on non-deleted properties
    whose ``property_type`` matches (ilike contains). Never returns description bodies.
    """
    et = (entity_type or "property").strip().lower()
    if et.endswith("s") and et not in ("property", "customer"):
        et = et[:-1]
    if et not in ("property", "customer"):
        et = "property"

    lim = max(1, min(int(limit or 25), 100))

    q = (
        db.session.query(
            VocabOccurrence.normalized_key,
            func.count(VocabOccurrence.id).label("cnt"),
            func.min(VocabOccurrence.entity_id).label("sample_id"),
            func.min(VocabOccurrence.field).label("sample_field"),
        )
        .filter(
            VocabOccurrence.entity_type == et,
            VocabOccurrence.status == "active",
        )
    )
    if field:
        q = q.filter(VocabOccurrence.field == field)

    if et == "property":
        # Exclude soft-deleted properties via join
        q = q.join(
            Property,
            (Property.id == VocabOccurrence.entity_id)
            & (Property.is_deleted.is_(False)),
        )
        if property_type:
            q = q.filter(Property.property_type.ilike(f"%{property_type}%"))
    # customers: no property_type filter; soft-delete handled at reindex time

    q = (
        q.group_by(VocabOccurrence.normalized_key)
        .order_by(func.count(VocabOccurrence.id).desc(), VocabOccurrence.normalized_key.asc())
        .limit(lim)
    )

    rows = q.all()
    out: List[Dict[str, Any]] = []
    for key, cnt, sample_id, sample_field in rows:
        term = VocabTerm.query.filter_by(normalized_key=key, status="active").first()
        out.append(
            {
                "normalized_key": key,
                "field": field or sample_field,
                "count": int(cnt or 0),
                "sample_entity_ids": [int(sample_id)] if sample_id is not None else [],
                "term_id": term.id if term else None,
                "canonical": term.canonical if term else None,
            }
        )
    return out

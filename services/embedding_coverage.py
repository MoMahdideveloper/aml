"""Property embedding coverage metrics (no provider calls)."""

from __future__ import annotations

from typing import Any, Dict, List

from database import db
from sqlalchemy_models import Property, PropertyEmbedding


def summarize_property_embedding_coverage() -> Dict[str, Any]:
    """
    Count active non-deleted properties vs those with a PropertyEmbedding row.

    When there are zero active properties, coverage is 1.0 (vacuously complete).
    """
    # Non-deleted properties form the hybrid candidate pool denominator.
    active = Property.query.filter(Property.is_deleted.is_(False)).count()

    if active == 0:
        return {
            "active_properties": 0,
            "with_embedding": 0,
            "missing": 0,
            "coverage": 1.0,
        }

    with_emb = (
        db.session.query(PropertyEmbedding.property_id)
        .join(Property, Property.id == PropertyEmbedding.property_id)
        .filter(Property.is_deleted.is_(False))
        .distinct()
        .count()
    )
    missing = max(0, active - with_emb)
    coverage = float(with_emb) / float(active)
    return {
        "active_properties": int(active),
        "with_embedding": int(with_emb),
        "missing": int(missing),
        "coverage": round(coverage, 4),
    }


def list_properties_missing_embeddings(*, limit: int = 50) -> List[int]:
    """Return up to ``limit`` active property ids that lack an embedding row."""
    lim = max(1, min(int(limit or 50), 500))
    subq = db.session.query(PropertyEmbedding.property_id)
    rows = (
        Property.query.filter(Property.is_deleted.is_(False))
        .filter(~Property.id.in_(subq))
        .order_by(Property.id.asc())
        .limit(lim)
        .all()
    )
    return [int(p.id) for p in rows]

"""Propagate soft-delete into derived intelligence indexes (best-effort)."""

from __future__ import annotations

from typing import Any, Dict

from database import db
from utils.observability import log_event


def cleanup_property_derived(property_id: int) -> Dict[str, Any]:
    """
    After a property is soft-deleted: remove embedding, deactivate occurrences,
    drop relationship edges touching the property. Fail-open per subsystem.
    """
    summary: Dict[str, Any] = {
        "entity_type": "property",
        "entity_id": int(property_id),
        "embedding_deleted": False,
        "occurrences_deactivated": 0,
        "edges_deleted": 0,
    }
    pid = int(property_id)

    try:
        from sqlalchemy_models import PropertyEmbedding

        emb = PropertyEmbedding.query.filter_by(property_id=pid).first()
        if emb:
            db.session.delete(emb)
            summary["embedding_deleted"] = True
    except Exception:
        pass

    try:
        from sqlalchemy_models import VocabOccurrence

        rows = VocabOccurrence.query.filter_by(
            entity_type="property", entity_id=pid, status="active"
        ).all()
        for row in rows:
            row.status = "inactive"
            summary["occurrences_deactivated"] += 1
    except Exception:
        pass

    try:
        from sqlalchemy_models import RelationshipEdge

        edges = RelationshipEdge.query.filter(
            (
                (RelationshipEdge.src_type == "property")
                & (RelationshipEdge.src_id == pid)
            )
            | (
                (RelationshipEdge.dst_type == "property")
                & (RelationshipEdge.dst_id == pid)
            )
        ).all()
        for e in edges:
            db.session.delete(e)
            summary["edges_deleted"] += 1
    except Exception:
        pass

    try:
        db.session.flush()
    except Exception:
        pass

    log_event(
        "intelligence_cleanup_property",
        component="intelligence_cleanup",
        entity_id=pid,
        embedding_deleted=summary["embedding_deleted"],
        occurrences_deactivated=summary["occurrences_deactivated"],
        edges_deleted=summary["edges_deleted"],
        # no free-text / titles
    )
    return summary


def cleanup_customer_derived(customer_id: int) -> Dict[str, Any]:
    """Deactivate customer occurrences and edges after soft-delete."""
    summary: Dict[str, Any] = {
        "entity_type": "customer",
        "entity_id": int(customer_id),
        "occurrences_deactivated": 0,
        "edges_deleted": 0,
    }
    cid = int(customer_id)
    try:
        from sqlalchemy_models import VocabOccurrence

        rows = VocabOccurrence.query.filter_by(
            entity_type="customer", entity_id=cid, status="active"
        ).all()
        for row in rows:
            row.status = "inactive"
            summary["occurrences_deactivated"] += 1
    except Exception:
        pass
    try:
        from sqlalchemy_models import RelationshipEdge

        edges = RelationshipEdge.query.filter(
            (
                (RelationshipEdge.src_type == "customer")
                & (RelationshipEdge.src_id == cid)
            )
            | (
                (RelationshipEdge.dst_type == "customer")
                & (RelationshipEdge.dst_id == cid)
            )
        ).all()
        for e in edges:
            db.session.delete(e)
            summary["edges_deleted"] += 1
    except Exception:
        pass
    try:
        db.session.flush()
    except Exception:
        pass
    log_event(
        "intelligence_cleanup_customer",
        component="intelligence_cleanup",
        entity_id=cid,
        occurrences_deactivated=summary["occurrences_deactivated"],
        edges_deleted=summary["edges_deleted"],
    )
    return summary

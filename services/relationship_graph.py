"""Lightweight SQL-backed relationship graph for CRM explainability (Track A)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from sqlalchemy import and_, or_

from database import db
from sqlalchemy_models import (
    Agent,
    Customer,
    Deal,
    Property,
    RelationshipEdge,
    _utcnow_naive,
)
from utils.observability import log_event

ENTITY_TYPES = frozenset({"customer", "property", "deal", "agent"})
EDGE_TYPES = frozenset(
    {
        "customer_deal",
        "deal_property",
        "customer_agent",
        "property_agent",
        "deal_agent",
    }
)


def feature_enabled() -> bool:
    return os.environ.get("ENABLE_DERIVED_EDGES", "0").strip() == "1"


class GraphError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _norm_type(entity_type: str) -> str:
    aliases = {
        "customers": "customer",
        "properties": "property",
        "deals": "deal",
        "agents": "agent",
    }
    t = (entity_type or "").strip().lower()
    t = aliases.get(t, t)
    if t not in ENTITY_TYPES:
        raise GraphError("bad_entity", f"Unsupported entity type: {entity_type}")
    return t


def _evidence(**kwargs: Any) -> str:
    # small JSON only — no free-text notes
    safe = {k: v for k, v in kwargs.items() if v is not None}
    return json.dumps(safe, separators=(",", ":"), default=str)[:500]


def _upsert_edge(
    *,
    src_type: str,
    src_id: int,
    dst_type: str,
    dst_id: int,
    edge_type: str,
    weight: float = 1.0,
    evidence: Optional[Dict[str, Any]] = None,
    run_id: str = "",
) -> RelationshipEdge:
    if edge_type not in EDGE_TYPES:
        raise GraphError("bad_edge", f"Unknown edge_type: {edge_type}")
    row = RelationshipEdge.query.filter_by(
        src_type=src_type,
        src_id=src_id,
        dst_type=dst_type,
        dst_id=dst_id,
        edge_type=edge_type,
    ).first()
    now = _utcnow_naive()
    payload = _evidence(**(evidence or {}))
    if row:
        row.weight = float(weight)
        row.evidence_json = payload
        row.computed_at = now
        row.source_run_id = (run_id or "")[:64]
    else:
        row = RelationshipEdge(
            src_type=src_type,
            src_id=int(src_id),
            dst_type=dst_type,
            dst_id=int(dst_id),
            edge_type=edge_type,
            weight=float(weight),
            evidence_json=payload,
            computed_at=now,
            source_run_id=(run_id or "")[:64],
        )
        db.session.add(row)
    return row


def _delete_edges_touching(entity_type: str, entity_id: int, edge_types: Optional[Sequence[str]] = None) -> int:
    q = RelationshipEdge.query.filter(
        or_(
            and_(RelationshipEdge.src_type == entity_type, RelationshipEdge.src_id == entity_id),
            and_(RelationshipEdge.dst_type == entity_type, RelationshipEdge.dst_id == entity_id),
        )
    )
    if edge_types:
        q = q.filter(RelationshipEdge.edge_type.in_(list(edge_types)))
    count = q.count()
    q.delete(synchronize_session=False)
    return count


def rebuild_for_entity(entity_type: str, entity_id: int) -> Dict[str, Any]:
    """Idempotent rebuild of edges touching this entity from live CRM FKs."""
    et = _norm_type(entity_type)
    eid = int(entity_id)
    run_id = uuid.uuid4().hex[:16]
    created = 0

    # Clear existing derived edges for this entity (our edge types only)
    _delete_edges_touching(et, eid, EDGE_TYPES)

    if et == "customer":
        c = Customer.query.filter_by(id=eid, is_deleted=False).first()
        if not c:
            raise GraphError("not_found", "Customer not found")
        deals = Deal.query.filter_by(customer_id=eid, is_deleted=False).all()
        for d in deals:
            _upsert_edge(
                src_type="customer",
                src_id=eid,
                dst_type="deal",
                dst_id=d.id,
                edge_type="customer_deal",
                evidence={"deal_status": d.status},
                run_id=run_id,
            )
            created += 1
            if d.property_id:
                _upsert_edge(
                    src_type="deal",
                    src_id=d.id,
                    dst_type="property",
                    dst_id=d.property_id,
                    edge_type="deal_property",
                    evidence={"deal_id": d.id},
                    run_id=run_id,
                )
                created += 1
            if d.agent_id:
                _upsert_edge(
                    src_type="customer",
                    src_id=eid,
                    dst_type="agent",
                    dst_id=d.agent_id,
                    edge_type="customer_agent",
                    evidence={"via_deal_id": d.id},
                    run_id=run_id,
                )
                created += 1
                _upsert_edge(
                    src_type="deal",
                    src_id=d.id,
                    dst_type="agent",
                    dst_id=d.agent_id,
                    edge_type="deal_agent",
                    evidence={},
                    run_id=run_id,
                )
                created += 1

    elif et == "property":
        p = Property.query.filter_by(id=eid, is_deleted=False).first()
        if not p:
            raise GraphError("not_found", "Property not found")
        if p.agent_id:
            _upsert_edge(
                src_type="property",
                src_id=eid,
                dst_type="agent",
                dst_id=p.agent_id,
                edge_type="property_agent",
                evidence={},
                run_id=run_id,
            )
            created += 1
        deals = Deal.query.filter_by(property_id=eid, is_deleted=False).all()
        for d in deals:
            _upsert_edge(
                src_type="deal",
                src_id=d.id,
                dst_type="property",
                dst_id=eid,
                edge_type="deal_property",
                evidence={"deal_status": d.status},
                run_id=run_id,
            )
            created += 1
            if d.customer_id:
                _upsert_edge(
                    src_type="customer",
                    src_id=d.customer_id,
                    dst_type="deal",
                    dst_id=d.id,
                    edge_type="customer_deal",
                    evidence={},
                    run_id=run_id,
                )
                created += 1
            if d.agent_id:
                _upsert_edge(
                    src_type="deal",
                    src_id=d.id,
                    dst_type="agent",
                    dst_id=d.agent_id,
                    edge_type="deal_agent",
                    evidence={},
                    run_id=run_id,
                )
                created += 1

    elif et == "deal":
        d = Deal.query.filter_by(id=eid, is_deleted=False).first()
        if not d:
            raise GraphError("not_found", "Deal not found")
        if d.customer_id:
            _upsert_edge(
                src_type="customer",
                src_id=d.customer_id,
                dst_type="deal",
                dst_id=eid,
                edge_type="customer_deal",
                evidence={"deal_status": d.status},
                run_id=run_id,
            )
            created += 1
        if d.property_id:
            _upsert_edge(
                src_type="deal",
                src_id=eid,
                dst_type="property",
                dst_id=d.property_id,
                edge_type="deal_property",
                evidence={},
                run_id=run_id,
            )
            created += 1
        if d.agent_id:
            _upsert_edge(
                src_type="deal",
                src_id=eid,
                dst_type="agent",
                dst_id=d.agent_id,
                edge_type="deal_agent",
                evidence={},
                run_id=run_id,
            )
            created += 1
            if d.customer_id:
                _upsert_edge(
                    src_type="customer",
                    src_id=d.customer_id,
                    dst_type="agent",
                    dst_id=d.agent_id,
                    edge_type="customer_agent",
                    evidence={"via_deal_id": eid},
                    run_id=run_id,
                )
                created += 1

    elif et == "agent":
        # listing agent + deal agent
        props = Property.query.filter_by(agent_id=eid, is_deleted=False).limit(200).all()
        for p in props:
            _upsert_edge(
                src_type="property",
                src_id=p.id,
                dst_type="agent",
                dst_id=eid,
                edge_type="property_agent",
                evidence={},
                run_id=run_id,
            )
            created += 1
        deals = Deal.query.filter_by(agent_id=eid, is_deleted=False).limit(200).all()
        for d in deals:
            _upsert_edge(
                src_type="deal",
                src_id=d.id,
                dst_type="agent",
                dst_id=eid,
                edge_type="deal_agent",
                evidence={},
                run_id=run_id,
            )
            created += 1
            if d.customer_id:
                _upsert_edge(
                    src_type="customer",
                    src_id=d.customer_id,
                    dst_type="agent",
                    dst_id=eid,
                    edge_type="customer_agent",
                    evidence={"via_deal_id": d.id},
                    run_id=run_id,
                )
                created += 1

    db.session.commit()
    log_event(
        "relationship_edges_rebuilt",
        component="relationship_graph",
        entity_type=et,
        entity_id=eid,
        edge_count=created,
        run_id=run_id,
    )
    return {"entity_type": et, "entity_id": eid, "edges_written": created, "run_id": run_id}


def _label_for(entity_type: str, entity_id: int) -> str:
    if entity_type == "customer":
        c = Customer.query.filter_by(id=entity_id).first()
        return (c.name if c else None) or f"Customer #{entity_id}"
    if entity_type == "property":
        p = Property.query.filter_by(id=entity_id).first()
        return (p.title if p else None) or f"Property #{entity_id}"
    if entity_type == "deal":
        return f"Deal #{entity_id}"
    if entity_type == "agent":
        a = Agent.query.filter_by(id=entity_id).first()
        return (a.name if a else None) or f"Agent #{entity_id}"
    return f"{entity_type}#{entity_id}"


def _url_for(entity_type: str, entity_id: int) -> str:
    try:
        from flask import url_for

        if entity_type == "customer":
            return url_for("customers.customer_360", customer_id=entity_id)
        if entity_type == "property":
            return url_for("properties.property_detail", property_id=entity_id)
        if entity_type == "deal":
            return url_for("deals.deals", highlight=entity_id)
        if entity_type == "agent":
            return url_for("agents.agent_dashboard", agent_id=entity_id)
    except Exception:
        pass
    paths = {
        "customer": f"/customers/{entity_id}",
        "property": f"/properties/{entity_id}",
        "deal": f"/deals?highlight={entity_id}",
        "agent": f"/agents/{entity_id}",
    }
    return paths.get(entity_type, f"/{entity_type}/{entity_id}")


def neighbors(
    entity_type: str,
    entity_id: int,
    *,
    depth: int = 1,
    rebuild_if_empty: bool = True,
) -> Dict[str, Any]:
    """1-hop neighbors by default. Rebuilds derived edges if none exist."""
    et = _norm_type(entity_type)
    eid = int(entity_id)
    depth = max(1, min(int(depth or 1), 2))

    existing = RelationshipEdge.query.filter(
        or_(
            and_(RelationshipEdge.src_type == et, RelationshipEdge.src_id == eid),
            and_(RelationshipEdge.dst_type == et, RelationshipEdge.dst_id == eid),
        )
    ).count()
    rebuilt = False
    if existing == 0 and rebuild_if_empty:
        try:
            rebuild_for_entity(et, eid)
            rebuilt = True
        except GraphError:
            raise
        except Exception as exc:
            log_event(
                "relationship_rebuild_failed",
                component="relationship_graph",
                entity_type=et,
                entity_id=eid,
                # no stack / PII
            )
            raise GraphError("rebuild_failed", "Could not rebuild edges") from exc

    rows = RelationshipEdge.query.filter(
        or_(
            and_(RelationshipEdge.src_type == et, RelationshipEdge.src_id == eid),
            and_(RelationshipEdge.dst_type == et, RelationshipEdge.dst_id == eid),
        )
    ).all()

    items: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, int, str]] = set()
    for row in rows:
        if row.src_type == et and row.src_id == eid:
            other_t, other_id = row.dst_type, row.dst_id
            direction = "out"
        else:
            other_t, other_id = row.src_type, row.src_id
            direction = "in"
        key = (other_t, other_id, row.edge_type)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "entity_type": other_t,
                "entity_id": other_id,
                "label": _label_for(other_t, other_id),
                "url": _url_for(other_t, other_id),
                "edge_type": row.edge_type,
                "direction": direction,
                "weight": row.weight,
            }
        )

    # depth=2: optional one more hop (ids only, no explosion)
    if depth >= 2 and items:
        hop2: List[Dict[str, Any]] = []
        for n in items[:20]:
            sub = neighbors(
                n["entity_type"],
                n["entity_id"],
                depth=1,
                rebuild_if_empty=False,
            )
            for s in sub.get("neighbors") or []:
                if s["entity_type"] == et and s["entity_id"] == eid:
                    continue
                hop2.append({**s, "via": n["edge_type"]})
        # de-dupe hop2
        seen2: Set[Tuple[str, int, str]] = set()
        hop2_u = []
        for s in hop2:
            k = (s["entity_type"], s["entity_id"], s.get("edge_type") or "")
            if k in seen2:
                continue
            seen2.add(k)
            hop2_u.append(s)
        return {
            "entity_type": et,
            "entity_id": eid,
            "neighbors": items,
            "neighbors_2hop": hop2_u[:40],
            "rebuilt": rebuilt,
        }

    return {
        "entity_type": et,
        "entity_id": eid,
        "neighbors": items,
        "rebuilt": rebuilt,
    }


class RelationshipGraphService:
    rebuild_for_entity = staticmethod(rebuild_for_entity)
    neighbors = staticmethod(neighbors)
    feature_enabled = staticmethod(feature_enabled)


relationship_graph_service = RelationshipGraphService()

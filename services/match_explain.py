"""Load property–customer match explanations for CRM UI (no raw PII dumps)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sqlalchemy_models import Property, PropertyMatch


def _parse_reasons(raw: str) -> List[str]:
    """Parse match_reasons JSON array or comma text into short strings."""
    text = (raw or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            out = []
            for item in data[:12]:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip()[:200])
                elif isinstance(item, dict):
                    # common shapes: {"reason": "..."} or {"text": "..."}
                    for k in ("reason", "text", "label", "message"):
                        if item.get(k):
                            out.append(str(item[k])[:200])
                            break
            return out
        if isinstance(data, str):
            return [data[:200]]
    except Exception:
        pass
    # plain text fallback
    parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
    return [p[:200] for p in parts[:12]]


def list_customer_matches(customer_id: int, *, limit: int = 10) -> List[Dict[str, Any]]:
    """Top matches for a customer with property title and short why list."""
    from sqlalchemy_models import Customer

    cust = Customer.query.filter_by(id=customer_id, is_deleted=False).first()
    if not cust:
        return []

    rows = (
        PropertyMatch.query.filter_by(customer_id=customer_id)
        .filter(PropertyMatch.status != "dismissed")
        .order_by(PropertyMatch.match_score.desc())
        .limit(max(1, min(limit, 30)))
        .all()
    )
    out: List[Dict[str, Any]] = []
    for m in rows:
        prop = Property.query.filter_by(id=m.property_id).first()
        if not prop or getattr(prop, "is_deleted", False):
            continue
        title = prop.title or f"Property #{m.property_id}"
        why = _parse_reasons(m.match_reasons or "")
        # Optional live score components when reasons empty (no provider call)
        score_components: Dict[str, Any] = {}
        if not why:
            try:
                from services.vector_service import vector_service

                breakdown = vector_service.score_breakdown(cust, prop)
                if isinstance(breakdown, dict):
                    score_components = {
                        k: float(v)
                        for k, v in breakdown.items()
                        if isinstance(v, (int, float))
                    }
                    why = [
                        f"{k}: {v:.2f}"
                        for k, v in list(score_components.items())[:8]
                    ]
            except Exception:
                pass
        out.append(
            {
                "match_id": m.id,
                "property_id": m.property_id,
                "property_title": title,
                "match_score": float(m.match_score or 0.0),
                "confidence_level": m.confidence_level or "",
                "status": m.status or "",
                "priority": m.priority or "",
                "why": why,
                "score_components": score_components,
            }
        )
    return out


def list_property_matches(property_id: int, *, limit: int = 10) -> List[Dict[str, Any]]:
    """Top customer matches for a property (ids + scores only; no customer PII in reasons dump)."""
    rows = (
        PropertyMatch.query.filter_by(property_id=property_id)
        .filter(PropertyMatch.status != "dismissed")
        .order_by(PropertyMatch.match_score.desc())
        .limit(max(1, min(limit, 30)))
        .all()
    )
    out: List[Dict[str, Any]] = []
    for m in rows:
        out.append(
            {
                "match_id": m.id,
                "customer_id": m.customer_id,
                "match_score": float(m.match_score or 0.0),
                "confidence_level": m.confidence_level or "",
                "status": m.status or "",
                "why": _parse_reasons(m.match_reasons or ""),
            }
        )
    return out

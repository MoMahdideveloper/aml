"""
Customer opportunities — multiple needs (briefs) per person.

Each brief is a separate goal:
  - buyer: find listings that fit
  - seller: comps + pipeline deals (cash-out / list)
  - exchange: trade current home for another
  - investor: cash / multi-unit style buying

Not agent KPIs — client-side opportunities only.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List, Optional


VALID_BRIEF_ROLES = ("buyer", "seller", "exchange", "investor")


def _property_image_url(prop) -> Optional[str]:
    """Best-effort public image path for Stitch-style property cards."""
    if not prop:
        return None
    filename = getattr(prop, "image_filename", None)
    if filename:
        return f"/static/uploads/{filename}"
    try:
        images = getattr(prop, "images", None) or []
        if images:
            first = images[0]
            url = getattr(first, "url", None)
            if url:
                return str(url)
            fn = getattr(first, "filename", None)
            if fn:
                return f"/static/uploads/{fn}"
    except Exception:
        pass
    return None


def normalize_brief_role(raw: Optional[str]) -> str:
    t = (raw or "buyer").strip().lower()
    if t in ("sell", "seller", "owner", "listing"):
        return "seller"
    if t in ("exchange", "swap", "trade", "moaveze", "معاوضه"):
        return "exchange"
    if t in ("investor", "investment", "cash"):
        return "investor"
    return "buyer"


def normalize_customer_type(raw: Optional[str]) -> str:
    """Legacy single role on customer (fallback when no briefs)."""
    t = (raw or "buyer").strip().lower()
    if t in ("investor", "investment"):
        return "investor"
    if t in ("both", "buyer_seller", "dual"):
        return "both"
    if t in ("seller", "sell", "owner"):
        return "seller"
    if t in ("exchange", "swap"):
        return "exchange"
    return "buyer"


def brief_as_pref_source(brief, customer) -> Any:
    """Object with customer-like fields for scoring from a brief."""
    return SimpleNamespace(
        id=getattr(customer, "id", None),
        name=getattr(customer, "name", ""),
        email=getattr(customer, "email", ""),
        phone=getattr(customer, "phone", ""),
        budget_min=getattr(brief, "budget_min", 0) or 0,
        budget_max=getattr(brief, "budget_max", 0) or 0,
        preferred_bedrooms=getattr(brief, "preferred_bedrooms", 0) or 0,
        preferred_bathrooms=getattr(brief, "preferred_bathrooms", 0) or 0,
        preferred_type=getattr(brief, "preferred_type", "") or "",
        location_preference=getattr(brief, "location_preference", "") or "",
        preferences=getattr(brief, "preferences", "") or "",
        status=getattr(customer, "status", "active"),
        customer_type=getattr(brief, "role", "buyer"),
    )


def ensure_default_brief(customer) -> Any:
    """If client has no briefs, create one from legacy customer fields."""
    from database import db
    from sqlalchemy_models import CustomerOpportunityBrief

    existing = (
        CustomerOpportunityBrief.query.filter_by(customer_id=customer.id, is_active=True)
        .order_by(CustomerOpportunityBrief.sort_order, CustomerOpportunityBrief.id)
        .all()
    )
    if existing:
        return existing

    role = normalize_customer_type(getattr(customer, "customer_type", None))
    if role == "both":
        role = "buyer"
    title_map = {
        "buyer": "Buy property",
        "seller": "Sell property",
        "exchange": "Exchange home",
        "investor": "Invest",
    }
    brief = CustomerOpportunityBrief(
        customer_id=customer.id,
        title=title_map.get(role, "Buy property"),
        role=role if role in VALID_BRIEF_ROLES else "buyer",
        budget_min=customer.budget_min or 0,
        budget_max=customer.budget_max or 0,
        preferred_bedrooms=customer.preferred_bedrooms or 0,
        preferred_bathrooms=customer.preferred_bathrooms or 0,
        preferred_type=customer.preferred_type or "",
        location_preference=customer.location_preference or "",
        preferences=customer.preferences or "",
        is_active=True,
        sort_order=0,
    )
    db.session.add(brief)
    db.session.commit()
    return [brief]


def list_briefs(customer_id: int, active_only: bool = True) -> List[Any]:
    from sqlalchemy_models import CustomerOpportunityBrief

    q = CustomerOpportunityBrief.query.filter_by(customer_id=customer_id)
    if active_only:
        q = q.filter_by(is_active=True)
    return q.order_by(CustomerOpportunityBrief.sort_order, CustomerOpportunityBrief.id).all()


def build_opportunities_for_brief(customer, brief, limit: int = 8) -> List[Dict[str, Any]]:
    """Generate opportunity cards for one brief."""
    role = normalize_brief_role(getattr(brief, "role", None))
    pref = brief_as_pref_source(brief, customer)

    if role in ("buyer", "investor"):
        return _buyer_side_opportunities(customer, brief, pref, limit=limit, role=role)
    if role == "exchange":
        return _exchange_opportunities(customer, brief, pref, limit=limit)
    return _seller_side_opportunities(customer, brief, pref, limit=limit)


def _buyer_side_opportunities(customer, brief, pref, limit: int, role: str = "buyer") -> List[Dict[str, Any]]:
    from sqlalchemy_models import Property
    from services.vector_service import vector_service

    props = (
        Property.query.filter_by(status="active", is_deleted=False)
        .order_by(Property.updated_at.desc())
        .limit(120)
        .all()
    )
    if not props:
        return []

    ranked = vector_service.search_properties(pref, props, top_k=limit)
    kind_label = "Investment opportunity" if role == "investor" else "Buying opportunity"
    out = []
    for rec in ranked:
        prop = rec.get("property")
        if not prop:
            continue
        score = int(round(float(rec.get("hybrid_score") or 0)))
        if score < 35:
            continue
        reasons = rec.get("match_reasons") or []
        reasons = [r for r in reasons if r and not str(r).startswith("Score mix:")][:3]
        price = getattr(prop, "price", None)
        try:
            price_f = float(price) if price is not None else None
        except (TypeError, ValueError):
            price_f = None
        out.append(
            {
                "id": f"b{brief.id}-p{prop.id}-{role}",
                "kind": role,
                "kind_label": kind_label,
                "brief_id": brief.id,
                "brief_title": brief.title,
                "title": prop.title or f"Property #{prop.id}",
                "subtitle": prop.address or prop.neighborhood or prop.property_type or "",
                "score": score,
                "status": "open",
                "reasons": reasons,
                "primary_url": f"/properties/{prop.id}",
                "primary_label": "View property",
                "customer_id": customer.id,
                "property_id": prop.id,
                "location": prop.neighborhood or prop.address or getattr(brief, "location_preference", "") or "",
                "preferred_type": prop.property_type or getattr(brief, "preferred_type", "") or "",
                "budget_min": getattr(brief, "budget_min", 0) or 0,
                "budget_max": getattr(brief, "budget_max", 0) or 0,
                "price": price_f,
                "bedrooms": getattr(prop, "bedrooms", None),
                "bathrooms": getattr(prop, "bathrooms", None),
                "square_feet": getattr(prop, "square_feet", None),
                "image_url": _property_image_url(prop),
                "meta": f"{brief.title} · fit {score}%",
            }
        )
    return out


def _seller_side_opportunities(customer, brief, pref, limit: int) -> List[Dict[str, Any]]:
    from database import db
    from sqlalchemy_models import Deal, Property
    from services.vector_service import VectorService

    out: List[Dict[str, Any]] = []
    vs = VectorService()
    pref_type = (pref.preferred_type or "").strip()
    loc = (pref.location_preference or "").strip()
    kind_pref = vs._normalize_property_kind(pref_type) if pref_type else ""

    # Deals for this client
    try:
        deals = (
            Deal.query.filter_by(customer_id=customer.id, is_deleted=False)
            .filter(Deal.status.notin_(["closed_won", "closed_lost", "won", "lost"]))
            .order_by(Deal.updated_at.desc())
            .limit(4)
            .all()
        )
    except Exception:
        deals = []

    for d in deals:
        prop = db.session.get(Property, d.property_id) if d.property_id else None
        out.append(
            {
                "id": f"b{brief.id}-deal{d.id}",
                "kind": "seller",
                "kind_label": "Deal opportunity",
                "brief_id": brief.id,
                "brief_title": brief.title,
                "title": prop.title if prop else f"Deal #{d.id}",
                "subtitle": f"Status: {d.status or 'open'}",
                "score": None,
                "status": d.status or "open",
                "reasons": ["Open deal for this client", brief.title],
                "primary_url": "/deals",
                "primary_label": "Open deals",
                "customer_id": customer.id,
                "property_id": d.property_id,
                "location": getattr(brief, "location_preference", "") or "",
                "preferred_type": getattr(brief, "preferred_type", "") or "",
                "budget_min": getattr(brief, "budget_min", 0) or 0,
                "budget_max": getattr(brief, "budget_max", 0) or 0,
                "meta": f"{brief.title} · pipeline",
            }
        )

    # Related property they want to sell
    if brief.related_property_id:
        own = db.session.get(Property, brief.related_property_id)
        if own:
            out.append(
                {
                    "id": f"b{brief.id}-own{own.id}",
                    "kind": "seller",
                    "kind_label": "Your listing focus",
                    "brief_id": brief.id,
                    "brief_title": brief.title,
                    "title": own.title or f"Property #{own.id}",
                    "subtitle": own.address or "Linked property to sell",
                    "score": None,
                    "status": own.status or "active",
                    "reasons": ["Linked as the home they want to sell"],
                    "primary_url": f"/properties/{own.id}",
                    "primary_label": "View home",
                    "customer_id": customer.id,
                    "property_id": own.id,
                    "location": own.neighborhood or own.address or "",
                    "preferred_type": own.property_type or "",
                    "budget_min": getattr(brief, "budget_min", 0) or 0,
                    "budget_max": getattr(brief, "budget_max", 0) or 0,
                    "meta": brief.title,
                }
            )

    # Market comps
    try:
        props = (
            Property.query.filter_by(status="active", is_deleted=False)
            .order_by(Property.updated_at.desc())
            .limit(80)
            .all()
        )
    except Exception:
        props = []

    scored = []
    for p in props:
        if brief.related_property_id and p.id == brief.related_property_id:
            continue
        kind = vs._normalize_property_kind(p.property_type or "")
        type_ok = (not kind_pref) or kind == kind_pref
        loc_ok = True
        if loc:
            hay = f"{p.neighborhood or ''} {p.address or ''}".lower()
            loc_ok = any(tok in hay for tok in loc.lower().replace(",", " ").split() if len(tok) > 1)
        if not type_ok and not loc_ok:
            continue
        score = 40 + (30 if type_ok else 0) + (25 if loc_ok else 0)
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    for score, p in scored[: max(0, limit - len(out))]:
        out.append(
            {
                "id": f"b{brief.id}-comp{p.id}",
                "kind": "seller",
                "kind_label": "Market opportunity",
                "brief_id": brief.id,
                "brief_title": brief.title,
                "title": p.title or f"Listing #{p.id}",
                "subtitle": p.address or p.neighborhood or "",
                "score": min(99, score),
                "status": "comp",
                "reasons": ["Comparable active listing", brief.title],
                "primary_url": f"/properties/{p.id}",
                "primary_label": "View listing",
                "customer_id": customer.id,
                "property_id": p.id,
                "location": p.neighborhood or p.address or "",
                "preferred_type": p.property_type or getattr(brief, "preferred_type", "") or "",
                "budget_min": getattr(brief, "budget_min", 0) or 0,
                "budget_max": getattr(brief, "budget_max", 0) or 0,
                "meta": f"{brief.title} · comp {min(99, score)}%",
            }
        )
    return out[:limit]


def _exchange_opportunities(customer, brief, pref, limit: int) -> List[Dict[str, Any]]:
    """Exchange: keep an eye on target homes + note their current home."""
    from database import db
    from sqlalchemy_models import Property

    out: List[Dict[str, Any]] = []
    if brief.related_property_id:
        own = db.session.get(Property, brief.related_property_id)
        if own:
            out.append(
                {
                    "id": f"b{brief.id}-exown{own.id}",
                    "kind": "exchange",
                    "kind_label": "Home to exchange",
                    "brief_id": brief.id,
                    "brief_title": brief.title,
                    "title": own.title or f"Property #{own.id}",
                    "subtitle": own.address or "Current home they want to trade",
                    "score": None,
                    "status": "owned",
                    "reasons": [
                        "Their side of the exchange",
                        (brief.exchange_notes or "")[:120] or "Set exchange notes on this brief",
                    ],
                    "primary_url": f"/properties/{own.id}",
                    "primary_label": "View home",
                    "customer_id": customer.id,
                    "property_id": own.id,
                    "location": own.neighborhood or own.address or "",
                    "preferred_type": own.property_type or "",
                    "budget_min": getattr(brief, "budget_min", 0) or 0,
                    "budget_max": getattr(brief, "budget_max", 0) or 0,
                    "meta": brief.title,
                }
            )

    # Target homes (buyer-side under exchange)
    targets = _buyer_side_opportunities(customer, brief, pref, limit=max(4, limit - len(out)), role="buyer")
    for t in targets:
        t["kind"] = "exchange"
        t["kind_label"] = "Exchange target"
        t["meta"] = f"{brief.title} · target fit {t.get('score', '—')}%"
        t["reasons"] = (t.get("reasons") or [])[:2] + ["Possible home to trade into"]
        out.append(t)
    return out[:limit]


def build_customer_briefs_with_opportunities(customer, limit_per_brief: int = 6) -> Dict[str, Any]:
    """
    Full payload for AI Match client page: list of briefs, each with opportunities.
    """
    briefs = ensure_default_brief(customer)
    sections = []
    total_ops = 0
    for brief in briefs:
        ops = build_opportunities_for_brief(customer, brief, limit=limit_per_brief)
        total_ops += len(ops)
        sections.append(
            {
                "brief": brief.to_dict() if hasattr(brief, "to_dict") else brief,
                "opportunities": ops,
                "count": len(ops),
            }
        )
    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "brief_count": len(sections),
        "opportunity_count": total_ops,
        "sections": sections,
        "empty_hint": (
            "Add a need below: e.g. Buy apartment, Sell villa, Exchange home, or Invest cash. "
            "Each need has its own preferences and opportunity list."
        ),
    }


# Back-compat shims used by older call sites
def build_customer_opportunities(customer, buyer_match_rows=None, limit: int = 12) -> Dict[str, Any]:
    data = build_customer_briefs_with_opportunities(customer, limit_per_brief=max(4, limit // 2))
    flat = []
    for sec in data["sections"]:
        flat.extend(sec["opportunities"])
    return {
        "customer_id": data["customer_id"],
        "customer_name": data["customer_name"],
        "customer_type": normalize_customer_type(getattr(customer, "customer_type", None)),
        "roles": [s["brief"].get("role") for s in data["sections"]],
        "count": len(flat[:limit]),
        "opportunities": flat[:limit],
        "sections": data["sections"],
        "empty_hint": data["empty_hint"],
    }


def customer_roles(customer) -> List[str]:
    t = normalize_customer_type(getattr(customer, "customer_type", None))
    if t in ("both", "investor"):
        return ["buyer", "seller"]
    if t == "exchange":
        return ["exchange"]
    return [t]

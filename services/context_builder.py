"""Allowlisted AI context packets with budgets and field provenance."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, FrozenSet


from sqlalchemy_models import (
    Agent,
    Customer,
    CustomerInteraction,
    CustomerOpportunityBrief,
    Deal,
    DealStageHistory,
    Property,
    PropertyFavorite,
    PropertyMatch,
    Task,
    _utcnow_naive,
)


from utils.observability import log_event

ENTITY_TYPES = frozenset({"customer", "property", "deal", "task", "agent"})
PURPOSES = frozenset({"match", "brief", "search_explain"})

# purpose → sections to keep (after full build); empty means keep all
PURPOSE_SECTION_PROFILES: Dict[str, Optional[Set[str]]] = {
    "brief": None,  # full packet subject to budget trim
    "match": frozenset(
        {
            "identity",
            "requirements",
            "listing",
            "matches",
            "opportunity_briefs",
            "deals",
            "concepts",
            "favorites",
            "completeness",
        }
    ),
    "search_explain": frozenset(
        {
            "identity",
            "listing",
            "requirements",
            "matches",
            "concepts",
            "description",
            "features",
            "completeness",
        }
    ),
}



# Default global char budget for serialized packet values
DEFAULT_MAX_CHARS = 8000
DESC_TRUNCATE = 400
MAX_DEALS = 8
MAX_INTERACTIONS = 10
MAX_STAGE_EVENTS = 12
MAX_FEATURES_CHARS = 300

# Keys that must never appear in packets
FORBIDDEN_KEYS = frozenset(
    {
        "password",
        "preferences",
        "notes",
        "body",
        "embedding",
        "embedding_data",
        "storage_key",
        "sha256",
        "secret",
        "api_key",
        "token",
    }
)


class ContextError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def feature_enabled() -> bool:
    try:
        from services.intelligence_settings import is_enabled

        return is_enabled("ai_context")
    except Exception:
        return os.environ.get("ENABLE_AI_CONTEXT", "0").strip() == "1"



def max_chars() -> int:
    try:
        return max(500, int(os.environ.get("AI_CONTEXT_MAX_CHARS", str(DEFAULT_MAX_CHARS))))
    except ValueError:
        return DEFAULT_MAX_CHARS


def _field(value: Any, source: str, *, as_of: Optional[datetime] = None) -> Dict[str, Any]:
    return {
        "value": value,
        "source": source,
        "as_of": (as_of or _utcnow_naive()).isoformat(),
    }


def _truncate(text: str, n: int) -> str:
    s = (text or "").strip()
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)].rstrip() + "…"


def _assert_no_forbidden(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in FORBIDDEN_KEYS or any(f in kl for f in ("password", "secret", "token")):
                raise ContextError("forbidden_key", f"Forbidden key in packet: {path}.{k}")
            _assert_no_forbidden(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_forbidden(item, f"{path}[{i}]")


def _estimate_chars(packet: Dict[str, Any]) -> int:
    import json

    try:
        return len(json.dumps(packet, default=str, ensure_ascii=False))
    except Exception:
        return 0


def _trim_packet(packet: Dict[str, Any], budget: int) -> Dict[str, Any]:
    """Drop lowest-priority sections until under budget."""
    if _estimate_chars(packet) <= budget:
        return packet
    packet.setdefault("meta", {})
    packet["meta"]["trimmed"] = True
    packet["meta"].setdefault("trimmed_fields", [])

    # Priority: core entity first, then deals, timeline, stage_history, description
    drop_order = [
        "stage_history",
        "timeline",
        "matches",
        "opportunity_briefs",
        "favorites",
        "deals",
        "concepts",
        "description",
        "features",
        "listing",
        "links",
        "requirements",
    ]

    sections = packet.get("sections")
    if isinstance(sections, dict):
        for inner in drop_order:
            if inner in sections:
                del sections[inner]
                packet["meta"]["trimmed_fields"].append(f"sections.{inner}")
                if _estimate_chars(packet) <= budget:
                    return packet
        # last resort: keep only identity
        keep = {}
        if "identity" in sections:
            keep["identity"] = sections["identity"]
        packet["sections"] = keep
        packet["meta"]["trimmed_fields"].append("sections.non_identity")
    return packet



@dataclass
class ContextPacket:
    entity_type: str
    entity_id: int
    purpose: str
    sections: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "purpose": self.purpose,
            "sections": self.sections,
            "meta": self.meta,
        }


class ContextBuilder:
    def build(
        self,
        entity_type: str,
        entity_id: int,
        *,
        purpose: str = "brief",
        actor_id: Optional[int] = None,
    ) -> ContextPacket:
        if not feature_enabled():
            raise ContextError("disabled", "AI context is disabled")

        et = (entity_type or "").strip().lower()
        # accept plural forms from URL
        aliases = {
            "customers": "customer",
            "properties": "property",
            "deals": "deal",
            "tasks": "task",
            "agents": "agent",
        }
        et = aliases.get(et, et)
        if et not in ENTITY_TYPES:
            raise ContextError("bad_entity", f"Unsupported entity_type: {entity_type}")

        purp = (purpose or "brief").strip().lower()
        if purp not in PURPOSES:
            raise ContextError("bad_purpose", f"Unsupported purpose: {purpose}")

        if et == "customer":
            packet = self._build_customer(entity_id, purpose=purp)
        elif et == "property":
            packet = self._build_property(entity_id, purpose=purp)
        elif et == "deal":
            packet = self._build_deal(entity_id, purpose=purp)
        elif et == "task":
            packet = self._build_task(entity_id, purpose=purp)
        else:
            packet = self._build_agent(entity_id, purpose=purp)

        # Attach vocabulary concepts when occurrence index is enabled
        try:
            from services.vocab.occurrences import list_for_entity, occurrences_feature_enabled

            if occurrences_feature_enabled():
                concepts = list_for_entity(et, entity_id, active_only=True)[:15]
                if concepts:
                    packet.sections["concepts"] = {
                        "items": [
                            {
                                "key": _field(c["normalized_key"], "vocab_occurrence.normalized_key"),
                                "field": _field(c["field"], "vocab_occurrence.field"),
                                "confidence": _field(c["confidence"], "vocab_occurrence.confidence"),
                            }
                            for c in concepts
                        ],
                        "untrusted_text": _field(False, "context_builder.policy"),
                    }
        except Exception:
            pass

        # Purpose profiles: drop non-priority sections before budget trim
        profile = PURPOSE_SECTION_PROFILES.get(purp)
        omitted: List[str] = []
        if profile is not None:
            keep = {}
            for sk, sv in packet.sections.items():
                if sk in profile or sk == "identity":
                    keep[sk] = sv
                else:
                    omitted.append(sk)
            packet.sections = keep
            packet.meta["purpose_profile"] = purp
            packet.meta["omitted_sections"] = omitted

        data = packet.to_dict()
        _assert_no_forbidden(data)
        data = _trim_packet(data, max_chars())
        data["meta"]["char_count"] = _estimate_chars(data)
        data["meta"]["char_budget"] = max_chars()
        data["meta"]["actor_id"] = actor_id



        log_event(
            "ai_context_built",
            component="context_builder",
            entity_type=et,
            entity_id=entity_id,
            purpose=purp,
            char_count=data["meta"]["char_count"],
            # never log packet body / PII values
        )
        return ContextPacket(
            entity_type=data["entity_type"],
            entity_id=data["entity_id"],
            purpose=data["purpose"],
            sections=data["sections"],
            meta=data["meta"],
        )

    def _build_customer(self, customer_id: int, *, purpose: str) -> ContextPacket:
        c = Customer.query.filter_by(id=customer_id, is_deleted=False).first()
        if not c:
            raise ContextError("not_found", "Customer not found")

        now = _utcnow_naive()
        sections: Dict[str, Any] = {
            "identity": {
                "id": _field(c.id, "customer.id", as_of=now),
                "name": _field(c.name, "customer.name", as_of=now),
                "status": _field(c.status, "customer.status", as_of=now),
                "customer_type": _field(
                    getattr(c, "customer_type", None) or "buyer",
                    "customer.customer_type",
                    as_of=now,
                ),
            },
            "requirements": {
                "budget_min": _field(c.budget_min, "customer.budget_min", as_of=now),
                "budget_max": _field(c.budget_max, "customer.budget_max", as_of=now),
                "preferred_type": _field(c.preferred_type, "customer.preferred_type", as_of=now),
                "preferred_bedrooms": _field(
                    c.preferred_bedrooms, "customer.preferred_bedrooms", as_of=now
                ),
                "preferred_bathrooms": _field(
                    c.preferred_bathrooms, "customer.preferred_bathrooms", as_of=now
                ),
                "location_preference": _field(
                    c.location_preference, "customer.location_preference", as_of=now
                ),
            },
            # deliberately omit: email, phone, customer.preferences free text
        }
        try:
            from services.customer_completeness import completeness_section_for_context

            sections["completeness"] = completeness_section_for_context(c)
        except Exception:
            pass

        deals = (
            Deal.query.filter_by(customer_id=c.id, is_deleted=False)
            .order_by(Deal.updated_at.desc())
            .limit(MAX_DEALS)
            .all()
        )
        deal_rows = []
        for d in deals:
            ptitle = None
            if d.property_id:
                prop = Property.query.filter_by(id=d.property_id).first()
                if prop and not prop.is_deleted:
                    ptitle = prop.title
            deal_rows.append(

                {
                    "id": _field(d.id, "deal.id", as_of=d.updated_at),
                    "status": _field(d.status, "deal.status", as_of=d.updated_at),
                    "offer_amount": _field(d.offer_amount, "deal.offer_amount", as_of=d.updated_at),
                    "property_title": _field(ptitle, "property.title", as_of=d.updated_at),
                    # no deal.notes
                }
            )
        if deal_rows:
            sections["deals"] = deal_rows

        # Property matches (scores only — no free-text reasons dump if large)
        matches = (
            PropertyMatch.query.filter_by(customer_id=c.id)
            .order_by(PropertyMatch.match_score.desc())
            .limit(8)
            .all()
        )
        if matches:
            mrows = []
            for m in matches:
                ptitle = None
                prop = Property.query.filter_by(id=m.property_id).first()
                if prop and not prop.is_deleted:
                    ptitle = prop.title
                mrows.append(
                    {
                        "property_id": _field(m.property_id, "property_match.property_id", as_of=m.created_at),
                        "property_title": _field(ptitle, "property.title", as_of=m.created_at),
                        "match_score": _field(m.match_score, "property_match.match_score", as_of=m.created_at),
                        "status": _field(m.status, "property_match.status", as_of=m.created_at),
                    }
                )
            sections["matches"] = mrows

        briefs = (
            CustomerOpportunityBrief.query.filter_by(customer_id=c.id, is_active=True)
            .order_by(CustomerOpportunityBrief.sort_order.asc())
            .limit(6)
            .all()
        )
        if briefs:
            sections["opportunity_briefs"] = [
                {
                    "id": _field(b.id, "customer_opportunity_brief.id", as_of=b.updated_at),
                    "title": _field(b.title, "customer_opportunity_brief.title", as_of=b.updated_at),
                    "role": _field(b.role, "customer_opportunity_brief.role", as_of=b.updated_at),
                    "budget_max": _field(b.budget_max, "customer_opportunity_brief.budget_max", as_of=b.updated_at),
                    "preferred_type": _field(
                        b.preferred_type, "customer_opportunity_brief.preferred_type", as_of=b.updated_at
                    ),
                    # omit preferences free text
                }
                for b in briefs
            ]

        # Timeline: types/dates only — never body/subject content
        interactions = (
            CustomerInteraction.query.filter_by(customer_id=c.id, is_deleted=False)
            .order_by(CustomerInteraction.occurred_at.desc())
            .limit(MAX_INTERACTIONS)
            .all()
        )

        if interactions:
            sections["timeline"] = [
                {
                    "id": _field(i.id, "customer_interaction.id", as_of=i.occurred_at),
                    "interaction_type": _field(
                        i.interaction_type, "customer_interaction.interaction_type", as_of=i.occurred_at
                    ),
                    "outcome": _field(i.outcome, "customer_interaction.outcome", as_of=i.occurred_at),
                    "occurred_at": _field(
                        i.occurred_at.isoformat() if i.occurred_at else None,
                        "customer_interaction.occurred_at",
                        as_of=i.occurred_at,
                    ),
                    "follow_up_at": _field(
                        i.follow_up_at.isoformat() if i.follow_up_at else None,
                        "customer_interaction.follow_up_at",
                        as_of=i.occurred_at,
                    ),
                    # no subject, no body
                }
                for i in interactions
            ]

        return ContextPacket(
            entity_type="customer",
            entity_id=c.id,
            purpose=purpose,
            sections=sections,
            meta={
                "schema_version": 1,
                "include_contact_pii": False,
                "include_note_bodies": False,
            },
        )

    def _build_property(self, property_id: int, *, purpose: str) -> ContextPacket:
        p = Property.query.filter_by(id=property_id, is_deleted=False).first()
        if not p:
            raise ContextError("not_found", "Property not found")

        now = p.updated_at or _utcnow_naive()
        sections: Dict[str, Any] = {
            "identity": {
                "id": _field(p.id, "property.id", as_of=now),
                "title": _field(p.title, "property.title", as_of=now),
                "file_code": _field(p.file_code, "property.file_code", as_of=now),
                "status": _field(p.status, "property.status", as_of=now),
            },
            "listing": {
                "property_type": _field(p.property_type, "property.property_type", as_of=now),
                "listing_type": _field(p.listing_type, "property.listing_type", as_of=now),
                "bedrooms": _field(p.bedrooms, "property.bedrooms", as_of=now),
                "bathrooms": _field(p.bathrooms, "property.bathrooms", as_of=now),
                "square_feet": _field(p.square_feet, "property.square_feet", as_of=now),
                "price": _field(p.price, "property.price", as_of=now),
                "neighborhood": _field(p.neighborhood, "property.neighborhood", as_of=now),
                "address": _field(p.address, "property.address", as_of=now),
            },
            "description": {
                "text": _field(
                    _truncate(p.description or "", DESC_TRUNCATE),
                    "property.description",
                    as_of=now,
                ),
                "truncated": _field(True, "context_builder.policy", as_of=now),
                "untrusted_text": _field(True, "context_builder.policy", as_of=now),
            },
            "features": {
                "text": _field(
                    _truncate(p.property_features or "", MAX_FEATURES_CHARS),
                    "property.property_features",
                    as_of=now,
                ),
                "untrusted_text": _field(True, "context_builder.policy", as_of=now),
            },
        }
        matches = (
            PropertyMatch.query.filter_by(property_id=p.id)
            .order_by(PropertyMatch.match_score.desc())
            .limit(8)
            .all()
        )
        if matches:
            sections["matches"] = [
                {
                    "customer_id": _field(m.customer_id, "property_match.customer_id", as_of=m.created_at),
                    "match_score": _field(m.match_score, "property_match.match_score", as_of=m.created_at),
                    "status": _field(m.status, "property_match.status", as_of=m.created_at),
                }
                for m in matches
            ]
        fav_count = PropertyFavorite.query.filter_by(property_id=p.id).count()
        sections["favorites"] = {
            "count": _field(fav_count, "property_favorite.count", as_of=now),
        }
        return ContextPacket(
            entity_type="property",
            entity_id=p.id,
            purpose=purpose,
            sections=sections,
            meta={"schema_version": 1},
        )

    def _build_task(self, task_id: int, *, purpose: str) -> ContextPacket:

        t = Task.query.filter_by(id=task_id, is_deleted=False).first()
        if not t:
            raise ContextError("not_found", "Task not found")
        now = t.created_at or _utcnow_naive()
        sections: Dict[str, Any] = {
            "identity": {
                "id": _field(t.id, "task.id", as_of=now),
                "title": _field(t.title, "task.title", as_of=now),
                "status": _field(t.status, "task.status", as_of=now),
                "priority": _field(t.priority, "task.priority", as_of=now),
            },
            "assignment": {
                "agent_id": _field(t.agent_id, "task.agent_id", as_of=now),
                "due_date": _field(
                    t.due_date.isoformat() if t.due_date else None,
                    "task.due_date",
                    as_of=now,
                ),
                "source_entity_type": _field(
                    t.source_entity_type, "task.source_entity_type", as_of=now
                ),
                "source_entity_id": _field(
                    t.source_entity_id, "task.source_entity_id", as_of=now
                ),
            },
            "description": {
                "text": _field(
                    _truncate(t.description or "", 200),
                    "task.description",
                    as_of=now,
                ),
                "truncated": _field(True, "context_builder.policy", as_of=now),
                "untrusted_text": _field(True, "context_builder.policy", as_of=now),
            },
        }
        return ContextPacket(
            entity_type="task",
            entity_id=t.id,
            purpose=purpose,
            sections=sections,
            meta={"schema_version": 1},
        )

    def _build_agent(self, agent_id: int, *, purpose: str) -> ContextPacket:
        a = Agent.query.filter_by(id=agent_id, is_deleted=False).first()
        if not a:
            raise ContextError("not_found", "Agent not found")
        now = a.created_at or _utcnow_naive()
        sections: Dict[str, Any] = {
            "identity": {
                "id": _field(a.id, "agent.id", as_of=now),
                "name": _field(a.name, "agent.name", as_of=now),
                "specialization": _field(
                    a.specialization, "agent.specialization", as_of=now
                ),
            },
            "stats": {
                "active_listings": _field(
                    a.active_listings, "agent.active_listings", as_of=now
                ),
                "total_sales": _field(a.total_sales, "agent.total_sales", as_of=now),
            },
            # deliberately omit email, phone, bio
        }
        return ContextPacket(
            entity_type="agent",
            entity_id=a.id,
            purpose=purpose,
            sections=sections,
            meta={"schema_version": 1, "include_contact_pii": False},
        )


    def _build_deal(self, deal_id: int, *, purpose: str) -> ContextPacket:
        d = Deal.query.filter_by(id=deal_id, is_deleted=False).first()
        if not d:
            raise ContextError("not_found", "Deal not found")

        now = d.updated_at or _utcnow_naive()
        cname = None
        ptitle = None
        if d.customer_id:
            cust = Customer.query.filter_by(id=d.customer_id).first()
            if cust and not cust.is_deleted:
                cname = cust.name
        if d.property_id:
            prop = Property.query.filter_by(id=d.property_id).first()
            if prop and not prop.is_deleted:
                ptitle = prop.title


        sections: Dict[str, Any] = {
            "identity": {
                "id": _field(d.id, "deal.id", as_of=now),
                "status": _field(d.status, "deal.status", as_of=now),
                "offer_amount": _field(d.offer_amount, "deal.offer_amount", as_of=now),
            },
            "links": {
                "customer_id": _field(d.customer_id, "deal.customer_id", as_of=now),
                "customer_name": _field(cname, "customer.name", as_of=now),
                "property_id": _field(d.property_id, "deal.property_id", as_of=now),
                "property_title": _field(ptitle, "property.title", as_of=now),
                "agent_id": _field(d.agent_id, "deal.agent_id", as_of=now),
            },
            # no deal.notes
        }

        hist = (
            DealStageHistory.query.filter_by(deal_id=d.id)
            .order_by(DealStageHistory.changed_at.desc())
            .limit(MAX_STAGE_EVENTS)
            .all()
        )
        if hist:
            sections["stage_history"] = [
                {
                    "from_stage": _field(h.from_stage, "deal_stage_history.from_stage", as_of=h.changed_at),
                    "to_stage": _field(h.to_stage, "deal_stage_history.to_stage", as_of=h.changed_at),
                    "changed_at": _field(
                        h.changed_at.isoformat() if h.changed_at else None,
                        "deal_stage_history.changed_at",
                        as_of=h.changed_at,
                    ),
                    "event_type": _field(h.event_type, "deal_stage_history.event_type", as_of=h.changed_at),
                }
                for h in hist
            ]

        return ContextPacket(
            entity_type="deal",
            entity_id=d.id,
            purpose=purpose,
            sections=sections,
            meta={"schema_version": 1, "include_freeform_notes": False},
        )



context_builder = ContextBuilder()

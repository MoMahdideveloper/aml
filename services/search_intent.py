"""Typed search intent from free-text queries (rule-based, no LLM)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set

from services.query_constraints import QueryConstraints, extract_constraints
from services.unified_search import ENTITY_SCOPES

# Lightweight scope cues in natural language
_SCOPE_CUES = {
    "customers": ("customer", "clients", "client", "buyer", "buyers"),
    "properties": ("property", "properties", "listing", "listings", "apartment", "villa", "house"),
    "deals": ("deal", "deals", "pipeline", "offer"),
    "tasks": ("task", "tasks", "todo", "follow-up", "follow up"),
    "agents": ("agent", "agents", "broker"),
    "activities": ("activity", "activities", "interaction", "interactions", "call", "email", "meeting"),
}


@dataclass
class SearchIntent:
    raw_query: str
    normalized_query: str
    scopes: Set[str] = field(default_factory=set)
    constraints: Optional[QueryConstraints] = None
    customer_constraints: Optional[Any] = None
    unresolved_phrases: List[str] = field(default_factory=list)
    hard_filters: Dict[str, Any] = field(default_factory=dict)
    soft_filters: Dict[str, Any] = field(default_factory=dict)
    customer_hard_filters: Dict[str, Any] = field(default_factory=dict)
    customer_soft_filters: Dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> Dict[str, Any]:
        out = {
            "scopes": sorted(self.scopes),
            "hard_filters": self.hard_filters,
            "soft_filters": self.soft_filters,
            "unresolved_phrases": self.unresolved_phrases[:10],
            "constraints": self.constraints.to_public_dict() if self.constraints else {},
            # deliberately omit raw_query from public/logs
        }
        if self.customer_hard_filters or self.customer_soft_filters:
            out["customer_hard_filters"] = self.customer_hard_filters
            out["customer_soft_filters"] = self.customer_soft_filters
            if self.customer_constraints is not None and hasattr(
                self.customer_constraints, "to_public_dict"
            ):
                out["customer_constraints"] = self.customer_constraints.to_public_dict()
        return out


def detect_scopes(query: str, requested: Optional[Set[str]] = None) -> Set[str]:
    """If client already selected scopes, keep them; else infer from cues or core default."""
    from services.unified_search import ALL_SCOPES, ENTITY_SCOPES

    if requested:
        return set(requested) & set(ALL_SCOPES) or set(ENTITY_SCOPES)
    q = (query or "").casefold()
    found: Set[str] = set()
    for scope, cues in _SCOPE_CUES.items():
        if any(c in q for c in cues):
            found.add(scope)
    # Default core five only (activities remain opt-in via explicit scope or cues).
    return found or set(ENTITY_SCOPES)


def interpret_query(
    query: str,
    *,
    requested_scopes: Optional[Set[str]] = None,
) -> SearchIntent:
    import re

    q = re.sub(r"\s+", " ", (query or "").strip())
    scopes = detect_scopes(q, requested_scopes)
    constraints = extract_constraints(q)
    # Optional LLM soft-fill (fail-open); never required for search
    try:
        from services.nl_query_parse import try_llm_fill_soft_constraints

        constraints = try_llm_fill_soft_constraints(q, constraints)
    except Exception:
        pass
    hard = constraints.hard_filters()
    soft = constraints.soft_filters()

    customer_constraints = None
    customer_hard: Dict[str, Any] = {}
    customer_soft: Dict[str, Any] = {}
    try:
        from services.customer_query_constraints import extract_customer_constraints

        customer_constraints = extract_customer_constraints(q)
        customer_hard = customer_constraints.hard_filters()
        customer_soft = customer_constraints.soft_filters()
    except Exception:
        pass

    # Unresolved: tokens not used in hard filters (heuristic)
    used = set()
    for v in hard.values():
        used.add(str(v).casefold())
    for v in soft.values():
        used.add(str(v).casefold())
    for v in customer_hard.values():
        used.add(str(v).casefold())
    for v in customer_soft.values():
        used.add(str(v).casefold())
    unresolved = []
    for tok in q.split():
        tl = tok.casefold().strip(".,")
        if len(tl) < 3:
            continue
        if tl.isdigit():
            continue
        if any(tl in str(u) or str(u) in tl for u in used):
            continue
        if tl in (
            "with",
            "near",
            "below",
            "above",
            "under",
            "find",
            "show",
            "looking",
            "for",
            "and",
            "the",
            "seeking",
            "customers",
            "customer",
        ):
            continue
        unresolved.append(tok)

    return SearchIntent(
        raw_query=q,
        normalized_query=q,
        scopes=scopes,
        constraints=constraints,
        customer_constraints=customer_constraints,
        unresolved_phrases=unresolved[:12],
        hard_filters=hard,
        soft_filters=soft,
        customer_hard_filters=customer_hard,
        customer_soft_filters=customer_soft,
    )

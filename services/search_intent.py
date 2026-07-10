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
}


@dataclass
class SearchIntent:
    raw_query: str
    normalized_query: str
    scopes: Set[str] = field(default_factory=set)
    constraints: Optional[QueryConstraints] = None
    unresolved_phrases: List[str] = field(default_factory=list)
    hard_filters: Dict[str, Any] = field(default_factory=dict)
    soft_filters: Dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "scopes": sorted(self.scopes),
            "hard_filters": self.hard_filters,
            "soft_filters": self.soft_filters,
            "unresolved_phrases": self.unresolved_phrases[:10],
            "constraints": self.constraints.to_public_dict() if self.constraints else {},
            # deliberately omit raw_query from public/logs
        }


def detect_scopes(query: str, requested: Optional[Set[str]] = None) -> Set[str]:
    """If client already selected scopes, keep them; else infer from cues or all."""
    if requested:
        return set(requested) & set(ENTITY_SCOPES) or set(ENTITY_SCOPES)
    q = (query or "").casefold()
    found: Set[str] = set()
    for scope, cues in _SCOPE_CUES.items():
        if any(c in q for c in cues):
            found.add(scope)
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
    hard = constraints.hard_filters()
    soft = constraints.soft_filters()

    # Unresolved: tokens not used in hard filters (heuristic)
    used = set()
    for v in hard.values():
        used.add(str(v).casefold())
    for v in soft.values():
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
        if tl in ("with", "near", "below", "above", "under", "find", "show", "looking", "for", "and", "the"):
            continue
        unresolved.append(tok)

    return SearchIntent(
        raw_query=q,
        normalized_query=q,
        scopes=scopes,
        constraints=constraints,
        unresolved_phrases=unresolved[:12],
        hard_filters=hard,
        soft_filters=soft,
    )

"""Canonical deal stages, normalization, and forecast probabilities."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Tuple

# Open pipeline order (index implies forward direction)
OPEN_STAGES: List[str] = [
    "prospecting",
    "contact_made",
    "property_shown",
    "offer_submitted",
    "negotiation",
]
WON_STAGE = "closed_won"
LOST_STAGE = "closed_lost"
TERMINAL_STAGES = frozenset({WON_STAGE, LOST_STAGE})
ALL_STAGES: List[str] = OPEN_STAGES + [WON_STAGE, LOST_STAGE]

PIPELINE_STAGES: List[Tuple[str, str]] = [
    ("prospecting", "Prospecting"),
    ("contact_made", "Contact Made"),
    ("property_shown", "Property Shown"),
    ("offer_submitted", "Offer Submitted"),
    ("negotiation", "Negotiation"),
    ("closed_won", "Closed Won"),
    ("closed_lost", "Closed Lost"),
]

STATUS_ALIASES = {
    "qualified": "prospecting",
    "lead": "prospecting",
    "new": "prospecting",
    "open": "prospecting",
    "active": "prospecting",
    "prospect": "prospecting",
    "contacted": "contact_made",
    "contact": "contact_made",
    "shown": "property_shown",
    "showing": "property_shown",
    "viewing": "property_shown",
    "offer": "offer_submitted",
    "offered": "offer_submitted",
    "submitted": "offer_submitted",
    "negotiating": "negotiation",
    "under_contract": "negotiation",
    "contract": "negotiation",
    "won": "closed_won",
    "closed": "closed_won",
    "sold": "closed_won",
    "lost": "closed_lost",
    "closed_lost": "closed_lost",
}

# Constrained 0..1 probabilities — single source for reports
STAGE_PROBABILITIES: Dict[str, Decimal] = {
    "prospecting": Decimal("0.10"),
    "contact_made": Decimal("0.20"),
    "property_shown": Decimal("0.35"),
    "offer_submitted": Decimal("0.50"),
    "negotiation": Decimal("0.70"),
    "closed_won": Decimal("1.00"),
    "closed_lost": Decimal("0.00"),
}


def normalize_deal_status(raw: Any) -> str:
    s = (str(raw or "prospecting")).strip().lower().replace(" ", "_").replace("-", "_")
    if s in set(ALL_STAGES):
        return s
    if s in STATUS_ALIASES:
        return STATUS_ALIASES[s]
    return "prospecting"


def is_open_stage(stage: str) -> bool:
    return normalize_deal_status(stage) in OPEN_STAGES


def stage_probability(stage: str) -> Decimal:
    key = normalize_deal_status(stage)
    p = STAGE_PROBABILITIES.get(key, Decimal("0.10"))
    if p < 0 or p > 1:
        raise ValueError(f"Invalid probability for {key}")
    return p


def stage_index(stage: str) -> int:
    key = normalize_deal_status(stage)
    if key in OPEN_STAGES:
        return OPEN_STAGES.index(key)
    if key == WON_STAGE:
        return len(OPEN_STAGES)
    if key == LOST_STAGE:
        return -1
    return 0


def is_forward_transition(from_stage: str, to_stage: str) -> bool:
    a, b = normalize_deal_status(from_stage), normalize_deal_status(to_stage)
    if b == LOST_STAGE:
        return False
    if a == LOST_STAGE:
        return True  # reopen/lost→open counted as entry, not forward conversion
    return stage_index(b) > stage_index(a)

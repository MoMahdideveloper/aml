"""Rule-based NL constraints for *customer* search (structured fields only).

Never uses free-text Customer.preferences. Hard filters only at high confidence.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from services.query_constraints import (
    HARD_CONFIDENCE,
    _PRICE_BARE_K_RE,
    _PRICE_OVER_RE,
    _PRICE_UNDER_RE,
    _TYPE_MAP,
    _parse_money,
    parse_bedrooms_min,
)

# Buyer/customer intent cues (scope hints, not hard filters alone)
_BUYER_CUES = re.compile(
    r"\b(?:seeking|looking\s+for|want(?:s|ing)?|need(?:s|ing)?|buyer|buyers|client|clients)\b",
    re.I,
)
_LOCATION_NEAR_RE = re.compile(
    r"\b(?:near|in|around|at)\s+([A-Za-z][A-Za-z0-9\s\-]{1,40})",
    re.I,
)


def feature_enabled() -> bool:
    """Env-only flag (no migration). Default off — preserves classic customer search."""
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            cfg = current_app.config.get("ENABLE_CUSTOMER_NL_FILTERS")
            if cfg is not None:
                return bool(cfg)
    except Exception:
        pass
    return os.environ.get("ENABLE_CUSTOMER_NL_FILTERS", "0").strip() == "1"


@dataclass
class CustomerQueryConstraints:
    preferred_type: Optional[str] = None
    preferred_bedrooms_min: Optional[int] = None
    budget_max: Optional[float] = None  # customer.budget_max <= this (or overlaps)
    budget_min: Optional[float] = None
    location_token: Optional[str] = None
    confidences: Dict[str, float] = field(default_factory=dict)

    def hard_filters(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        mapping = {
            "preferred_type": self.preferred_type,
            "preferred_bedrooms_min": self.preferred_bedrooms_min,
            "budget_max": self.budget_max,
            "budget_min": self.budget_min,
            "location_token": self.location_token,
        }
        for key, val in mapping.items():
            if val is None:
                continue
            if self.confidences.get(key, 0.0) >= HARD_CONFIDENCE:
                out[key] = val
        return out

    def soft_filters(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        hard = self.hard_filters()
        mapping = {
            "preferred_type": self.preferred_type,
            "preferred_bedrooms_min": self.preferred_bedrooms_min,
            "budget_max": self.budget_max,
            "budget_min": self.budget_min,
            "location_token": self.location_token,
        }
        for key, val in mapping.items():
            if val is None or key in hard:
                continue
            if self.confidences.get(key, 0.0) > 0:
                out[key] = val
        return out

    def chips(self) -> List[str]:
        chips: List[str] = []
        hard = self.hard_filters()
        if "preferred_type" in hard:
            chips.append(f"Wants type: {hard['preferred_type']}")
        if "preferred_bedrooms_min" in hard:
            chips.append(f"Beds ≥ {hard['preferred_bedrooms_min']}")
        if "budget_max" in hard:
            chips.append(f"Budget ≤ {int(hard['budget_max']):,}")
        if "budget_min" in hard:
            chips.append(f"Budget ≥ {int(hard['budget_min']):,}")
        if "location_token" in hard:
            chips.append(f"Location: {hard['location_token']}")
        for key, val in self.soft_filters().items():
            chips.append(f"Soft: {key}={val}")
        return chips

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "hard": self.hard_filters(),
            "soft": self.soft_filters(),
            "chips": self.chips(),
        }


def extract_customer_constraints(query: str) -> CustomerQueryConstraints:
    """Extract customer structured filters from free text. Never reads preferences body."""
    q = (query or "").strip()
    c = CustomerQueryConstraints()
    if not q:
        return c
    ql = q.casefold()

    beds = parse_bedrooms_min(q)
    if beds is not None:
        c.preferred_bedrooms_min = beds
        # slightly lower if no buyer cue
        c.confidences["preferred_bedrooms_min"] = 0.9 if _BUYER_CUES.search(q) else 0.85

    m = _PRICE_UNDER_RE.search(q)
    if m:
        c.budget_max = _parse_money(m.group(1), m.group(2))
        c.confidences["budget_max"] = 0.9
    else:
        m_k = _PRICE_BARE_K_RE.search(q)
        if m_k:
            c.budget_max = float(m_k.group(1)) * 1_000
            c.confidences["budget_max"] = 0.9

    m = _PRICE_OVER_RE.search(q)
    if m:
        c.budget_min = _parse_money(m.group(1), m.group(2))
        c.confidences["budget_min"] = 0.85

    for token, canonical in _TYPE_MAP.items():
        if re.search(rf"\b{re.escape(token)}\b", ql):
            c.preferred_type = canonical
            c.confidences["preferred_type"] = 0.85
            break

    m = _LOCATION_NEAR_RE.search(q)
    if m:
        loc = re.sub(r"\s+", " ", m.group(1).strip())
        # strip trailing noise words
        loc = re.sub(
            r"\b(?:under|below|above|with|for|apartment|villa|house|bedroom|bedrooms|br)\b.*$",
            "",
            loc,
            flags=re.I,
        ).strip(" ,.")
        if 2 <= len(loc) <= 40:
            c.location_token = loc
            c.confidences["location_token"] = 0.85

    return c


def customer_matches_hard(customer: Any, hard: Dict[str, Any]) -> bool:
    """SQL-aligned predicate for tests; repository applies equivalent filters."""
    if not hard:
        return True
    if "preferred_type" in hard:
        pt = (getattr(customer, "preferred_type", None) or "").casefold()
        want = str(hard["preferred_type"]).casefold()
        if want and want not in pt and pt != want:
            return False
    if "preferred_bedrooms_min" in hard:
        beds = int(getattr(customer, "preferred_bedrooms", 0) or 0)
        if beds < int(hard["preferred_bedrooms_min"]):
            return False
    if "budget_max" in hard:
        # customer can pay up to budget_max field; they "fit" under query max if
        # their budget_min is not already above the query max, and budget_max
        # (if set) overlaps the range.
        cmax = float(getattr(customer, "budget_max", 0) or 0)
        cmin = float(getattr(customer, "budget_min", 0) or 0)
        qmax = float(hard["budget_max"])
        if cmin > qmax:
            return False
        if cmax > 0 and cmax > qmax * 1.05:
            # allow small slack; prefer customers whose stated max is near/below
            return False
    if "budget_min" in hard:
        cmax = float(getattr(customer, "budget_max", 0) or 0)
        qmin = float(hard["budget_min"])
        if cmax > 0 and cmax < qmin:
            return False
    if "location_token" in hard:
        loc = (getattr(customer, "location_preference", None) or "").casefold()
        token = str(hard["location_token"]).casefold()
        if token and token not in loc:
            return False
    return True

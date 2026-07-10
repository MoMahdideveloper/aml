"""Rule-based NL constraint extract for property search (no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

HARD_CONFIDENCE = 0.8

# property_type keywords → canonical
_TYPE_MAP = {
    "villa": "villa",
    "house": "house",
    "home": "house",
    "apartment": "apartment",
    "apt": "apartment",
    "flat": "apartment",
    "condo": "condo",
    "condominium": "condo",
    "townhouse": "townhouse",
    "land": "land",
    "office": "office",
    "commercial": "commercial",
}

_BEDS_RE = re.compile(
    r"\b(\d+)\s*(?:bed(?:room)?s?|br)\b",
    re.IGNORECASE,
)
_BEDS_PLUS_RE = re.compile(
    r"\b(\d+)\+\s*(?:bed(?:room)?s?|br)\b",
    re.IGNORECASE,
)
_PRICE_UNDER_RE = re.compile(
    r"\b(?:under|below|max(?:imum)?|<=?)\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(k|m|million)?\b",
    re.IGNORECASE,
)
_PRICE_OVER_RE = re.compile(
    r"\b(?:over|above|min(?:imum)?|>=?)\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(k|m|million)?\b",
    re.IGNORECASE,
)
_PRICE_BARE_K_RE = re.compile(
    r"\b(?:under|below|max)\s*(\d+)\s*k\b",
    re.IGNORECASE,
)
_FOR_SALE_RE = re.compile(r"\bfor\s+sale\b|\bsale\b", re.IGNORECASE)
_FOR_RENT_RE = re.compile(r"\bfor\s+rent\b|\brent(?:al)?\b|\blease\b", re.IGNORECASE)


@dataclass
class QueryConstraints:
    property_type: Optional[str] = None
    bedrooms_min: Optional[int] = None
    price_max: Optional[float] = None
    price_min: Optional[float] = None
    listing_type: Optional[str] = None  # sale | rent
    confidences: Dict[str, float] = field(default_factory=dict)

    def hard_filters(self) -> Dict[str, Any]:
        """Fields with confidence >= HARD_CONFIDENCE for SQL/row hard filter."""
        out: Dict[str, Any] = {}
        mapping = {
            "property_type": self.property_type,
            "bedrooms_min": self.bedrooms_min,
            "price_max": self.price_max,
            "price_min": self.price_min,
            "listing_type": self.listing_type,
        }
        for key, val in mapping.items():
            if val is None:
                continue
            if self.confidences.get(key, 0.0) >= HARD_CONFIDENCE:
                out[key] = val
        return out

    def chips(self) -> List[str]:
        chips: List[str] = []
        hard = self.hard_filters()
        if "property_type" in hard:
            chips.append(f"Type: {hard['property_type']}")
        if "bedrooms_min" in hard:
            chips.append(f"Bedrooms ≥ {hard['bedrooms_min']}")
        if "price_max" in hard:
            chips.append(f"Price ≤ {int(hard['price_max']):,}")
        if "price_min" in hard:
            chips.append(f"Price ≥ {int(hard['price_min']):,}")
        if "listing_type" in hard:
            chips.append(f"Listing: {hard['listing_type']}")
        return chips

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "property_type": self.property_type,
            "bedrooms_min": self.bedrooms_min,
            "price_max": self.price_max,
            "price_min": self.price_min,
            "listing_type": self.listing_type,
            "hard": self.hard_filters(),
            "chips": self.chips(),
        }


def _parse_money(num_s: str, suffix: Optional[str]) -> float:
    n = float(num_s.replace(",", ""))
    if not suffix:
        return n
    s = suffix.lower()
    if s == "k":
        return n * 1_000
    if s in ("m", "million"):
        return n * 1_000_000
    return n


def extract_constraints(query: str) -> QueryConstraints:
    """Extract structured constraints from free text. High-confidence only for hard use."""
    q = (query or "").strip()
    c = QueryConstraints()
    if not q:
        return c
    ql = q.casefold()

    # bedrooms
    m = _BEDS_PLUS_RE.search(q) or _BEDS_RE.search(q)
    if m:
        beds = int(m.group(1))
        if 0 < beds <= 20:
            c.bedrooms_min = beds
            c.confidences["bedrooms_min"] = 0.9

    # price
    m = _PRICE_UNDER_RE.search(q)
    if m:
        c.price_max = _parse_money(m.group(1), m.group(2))
        c.confidences["price_max"] = 0.9
    else:
        m_k = _PRICE_BARE_K_RE.search(q)
        if m_k:
            c.price_max = float(m_k.group(1)) * 1_000
            c.confidences["price_max"] = 0.9

    m = _PRICE_OVER_RE.search(q)
    if m:
        c.price_min = _parse_money(m.group(1), m.group(2))
        c.confidences["price_min"] = 0.9


    # listing type — prefer explicit phrases
    # listing_type values align with Property.listing_type (sale | rental)
    if re.search(r"\bfor\s+rent\b|\brental\b|\blease\b", q, re.I):
        c.listing_type = "rental"
        c.confidences["listing_type"] = 0.9
    elif re.search(r"\bfor\s+sale\b", q, re.I):
        c.listing_type = "sale"
        c.confidences["listing_type"] = 0.9


    # property type — whole word match
    for token, canonical in _TYPE_MAP.items():
        if re.search(rf"\b{re.escape(token)}\b", ql):
            c.property_type = canonical
            c.confidences["property_type"] = 0.85
            break

    return c


def property_matches_hard(prop: Any, hard: Dict[str, Any]) -> bool:
    """Return True if property row satisfies hard filters."""
    if not hard:
        return True
    if "property_type" in hard:
        pt = (getattr(prop, "property_type", None) or "").casefold()
        want = str(hard["property_type"]).casefold()
        if want not in pt and pt != want:
            # allow loose contains
            if want not in pt:
                return False
    if "bedrooms_min" in hard:
        beds = getattr(prop, "bedrooms", None)
        if beds is None or int(beds) < int(hard["bedrooms_min"]):
            return False
    if "price_max" in hard:
        price = getattr(prop, "price", None)
        if price is None or float(price) > float(hard["price_max"]):
            return False
    if "price_min" in hard:
        price = getattr(prop, "price", None)
        if price is None or float(price) < float(hard["price_min"]):
            return False
    if "listing_type" in hard:
        lt = (getattr(prop, "listing_type", None) or "").casefold()
        want = str(hard["listing_type"]).casefold()
        # accept rent/rental synonyms
        aliases = {want}
        if want in ("rent", "rental"):
            aliases.update({"rent", "rental"})
        if lt and lt not in aliases and not any(a in lt for a in aliases):
            return False
        # if listing_type empty on model, do not hard-fail
    return True


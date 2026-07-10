"""Optional LLM-assisted constraint parse — fail-open, never required for search."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional

from services.query_constraints import HARD_CONFIDENCE, QueryConstraints
from utils.observability import log_event

_ALLOWED_KEYS = frozenset(
    {"property_type", "bedrooms_min", "price_max", "price_min", "listing_type"}
)


def feature_enabled() -> bool:
    try:
        from services.intelligence_settings import is_enabled

        return is_enabled("nl_query_parse")
    except Exception:
        return os.environ.get("ENABLE_NL_QUERY_PARSE", "0").strip() == "1"


def _safe_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = fenced.group(1) if fenced else None
    if not raw:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        raw = m.group(0) if m else None
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def try_llm_fill_soft_constraints(
    query: str,
    base: QueryConstraints,
) -> QueryConstraints:
    """
    If flag on and LLM available, fill only missing constraint fields as *soft*
    (confidence below hard threshold). Never overrides high-confidence rule fields.
    On any failure, returns base unchanged (fail-open).
    """
    if not feature_enabled():
        return base
    if not (query or "").strip():
        return base

    # Skip if already fully constrained by rules
    if base.hard_filters() and len(base.hard_filters()) >= 2:
        return base

    try:
        from services.llm import llm_provider

        if not getattr(llm_provider, "is_available", False):
            log_event(
                "nl_query_parse_skipped",
                component="nl_query_parse",
                reason="provider_unavailable",
            )
            return base

        prompt = (
            "Extract real-estate search constraints as JSON only. "
            "Keys allowed: property_type (string), bedrooms_min (int), "
            "price_max (number), price_min (number), listing_type (sale|rental). "
            "Omit unknown keys. No markdown.\n"
            f"Query: {query[:200]}\n"
        )
        # Never log prompt/query body
        raw = llm_provider.generate_market_analysis(prompt)
        data = _safe_json_object(str(raw or ""))
        if not data:
            log_event(
                "nl_query_parse_skipped",
                component="nl_query_parse",
                reason="parse_failed",
            )
            return base

        # Soft-only confidence so hard filters stay rule-based unless already high
        soft_conf = HARD_CONFIDENCE - 0.15  # 0.65 → soft

        if "property_type" in data and not base.property_type:
            pt = str(data.get("property_type") or "").strip().lower()
            if pt and len(pt) <= 40:
                base.property_type = pt
                base.confidences["property_type"] = soft_conf

        if "bedrooms_min" in data and base.bedrooms_min is None:
            try:
                beds = int(data["bedrooms_min"])
                if 0 < beds <= 20:
                    base.bedrooms_min = beds
                    base.confidences["bedrooms_min"] = soft_conf
            except (TypeError, ValueError):
                pass

        if "price_max" in data and base.price_max is None:
            try:
                base.price_max = float(data["price_max"])
                base.confidences["price_max"] = soft_conf
            except (TypeError, ValueError):
                pass

        if "price_min" in data and base.price_min is None:
            try:
                base.price_min = float(data["price_min"])
                base.confidences["price_min"] = soft_conf
            except (TypeError, ValueError):
                pass

        if "listing_type" in data and not base.listing_type:
            lt = str(data.get("listing_type") or "").strip().lower()
            if lt in ("sale", "rent", "rental"):
                base.listing_type = "rental" if lt in ("rent", "rental") else "sale"
                base.confidences["listing_type"] = soft_conf

        log_event(
            "nl_query_parse_applied",
            component="nl_query_parse",
            soft_keys=len(base.soft_filters()),
        )
        return base
    except Exception:
        log_event(
            "nl_query_parse_skipped",
            component="nl_query_parse",
            reason="exception",
        )
        return base

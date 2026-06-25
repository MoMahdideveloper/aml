import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from database import db
from extensions import cache
from sqlalchemy_models import Customer, Deal, Property, PropertyFavorite
from utils.execution_tracer import log_execution


logger = logging.getLogger("services.proptech_scoring")

_CACHE_TTL_SECONDS = int(os.environ.get("PROPTECH_SCORE_CACHE_TTL_SECONDS", "86400"))
_HOT_LEAD_THRESHOLD = int(os.environ.get("HOT_LEAD_THRESHOLD", "85"))
_RARE_FIND_THRESHOLD = int(os.environ.get("RARE_FIND_THRESHOLD", "85"))


@log_execution
def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


@log_execution
def _clamp_score(value: int) -> int:
    return max(0, min(100, int(value)))


@log_execution
def _cache_get(key: str) -> Optional[int]:
    try:
        value = cache.get(key)
    except Exception:
        return None
    parsed = _safe_int(value, default=-1)
    return parsed if parsed >= 0 else None


@log_execution
def _cache_set(key: str, value: int) -> None:
    try:
        cache.set(key, _clamp_score(value), timeout=_CACHE_TTL_SECONDS)
    except Exception:
        logger.debug("Score cache set failed for key=%s", key)


@log_execution
def _customer_score_key(customer_id: int) -> str:
    return f"proptech:customer_score:{int(customer_id)}"


@log_execution
def _property_score_key(property_id: int) -> str:
    return f"proptech:property_score:{int(property_id)}"


@log_execution
def _parse_json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    raw = str(value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return {}
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


@log_execution
def _normalize_string_list(value: Any, limit: int = 5) -> List[str]:
    if not isinstance(value, list):
        return []
    normalized: List[str] = []
    for item in value[:limit]:
        text = str(item or "").strip()
        if text:
            normalized.append(text)
    return normalized


@log_execution
def extract_property_smart_context(property_obj: Property) -> Dict[str, Any]:
    payload = _parse_json_dict(getattr(property_obj, "custom_fields", ""))
    smart_benefits_raw = payload.get("smart_benefits")
    trending_badges_raw = payload.get("trending_badges")

    smart_benefits: List[Dict[str, str]] = []
    if isinstance(smart_benefits_raw, list):
        for item in smart_benefits_raw[:5]:
            if isinstance(item, dict):
                benefit = str(item.get("benefit") or "").strip()
                feature = str(item.get("feature") or "").strip()
                if benefit:
                    row: Dict[str, str] = {"benefit": benefit}
                    if feature:
                        row["feature"] = feature
                    smart_benefits.append(row)
            elif isinstance(item, str):
                text = item.strip()
                if text:
                    smart_benefits.append({"benefit": text})

    return {
        "smart_benefits": smart_benefits,
        "trending_badges": _normalize_string_list(trending_badges_raw),
    }


@log_execution
def _get_customer_ai_profile(customer: Customer) -> Dict[str, Any]:
    payload = _parse_json_dict(getattr(customer, "preferences", ""))
    for key in ("ai_profile", "copilot_profile", "profile"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


@log_execution
def _get_customer_last_activity(customer: Customer) -> Optional[datetime]:
    last_deal_activity = (
        db.session.query(func.max(Deal.updated_at))
        .filter(Deal.customer_id == customer.id, Deal.is_deleted.is_(False))
        .scalar()
    )
    if last_deal_activity:
        return last_deal_activity
    created_at = getattr(customer, "created_at", None)
    return created_at if isinstance(created_at, datetime) else None


@log_execution
def calculate_customer_score(customer: Customer, now: Optional[datetime] = None) -> int:
    now = now or datetime.utcnow()
    score = 0
    status = str(getattr(customer, "status", "") or "").strip().lower()
    preferences_text = str(getattr(customer, "preferences", "") or "").lower()

    if any(token in preferences_text for token in ("pre-approved", "preapproved", "mortgage approved")):
        score += 40
    if status == "active":
        score += 20

    active_deals_count = (
        db.session.query(Deal)
        .filter(
            Deal.customer_id == customer.id,
            Deal.is_deleted.is_(False),
            Deal.status.notin_(["closed_lost"]),
        )
        .count()
    )
    if active_deals_count >= 3:
        score += 15
    elif active_deals_count > 0:
        score += 10

    if any(token in preferences_text for token in ("mortgage", "loan", "pre-qual")):
        score += 10

    profile = _get_customer_ai_profile(customer)
    if bool(profile.get("is_real_seller")) and str(profile.get("urgency", "")).lower() == "high":
        score += 30

    last_activity = _get_customer_last_activity(customer)
    if last_activity and (now - last_activity) > timedelta(days=60):
        score -= 30

    return _clamp_score(score)


@log_execution
def build_neighborhood_price_per_sqm(properties: List[Property]) -> Dict[str, float]:
    totals: Dict[str, float] = {}
    counts: Dict[str, int] = {}

    for property_obj in properties:
        neighborhood = str(getattr(property_obj, "neighborhood", "") or "").strip().lower()
        square_feet = _safe_int(getattr(property_obj, "square_feet", 0), default=0)
        price = _safe_int(getattr(property_obj, "price", 0), default=0)
        if not neighborhood or square_feet <= 0 or price <= 0:
            continue
        totals[neighborhood] = totals.get(neighborhood, 0.0) + (price / square_feet)
        counts[neighborhood] = counts.get(neighborhood, 0) + 1

    return {
        neighborhood: totals[neighborhood] / max(1, counts.get(neighborhood, 0))
        for neighborhood in totals.keys()
    }


@log_execution
def build_recent_favorites_map(hours: int = 48) -> Dict[int, int]:
    since = datetime.utcnow() - timedelta(hours=max(1, hours))
    rows = (
        db.session.query(PropertyFavorite.property_id, func.count(PropertyFavorite.id))
        .filter(PropertyFavorite.created_at >= since)
        .group_by(PropertyFavorite.property_id)
        .all()
    )
    return {int(property_id): int(count) for property_id, count in rows}


@log_execution
def calculate_property_score(
    property_obj: Property,
    neighborhood_benchmarks: Optional[Dict[str, float]] = None,
    recent_favorites_map: Optional[Dict[int, int]] = None,
) -> int:
    score = 0
    neighborhood = str(getattr(property_obj, "neighborhood", "") or "").strip().lower()
    square_feet = _safe_int(getattr(property_obj, "square_feet", 0), default=0)
    price = _safe_int(getattr(property_obj, "price", 0), default=0)

    neighborhood_avg = 0.0
    if neighborhood_benchmarks and neighborhood:
        neighborhood_avg = float(neighborhood_benchmarks.get(neighborhood, 0.0) or 0.0)
    if square_feet > 0 and price > 0 and neighborhood_avg > 0:
        price_per_sqm = price / square_feet
        if price_per_sqm <= neighborhood_avg * 0.95:
            score += 30
        elif price_per_sqm <= neighborhood_avg:
            score += 20
        elif price_per_sqm <= neighborhood_avg * 1.05:
            score += 10

    recent_favorites = 0
    property_id = _safe_int(getattr(property_obj, "id", None), default=0)
    if recent_favorites_map and property_id > 0:
        recent_favorites = int(recent_favorites_map.get(property_id, 0) or 0)

    if recent_favorites >= 20:
        score += 20
    elif recent_favorites >= 10:
        score += 12
    elif recent_favorites > 0:
        score += 5

    smart_context = extract_property_smart_context(property_obj)
    trending_count = len(smart_context.get("trending_badges", []))
    if trending_count > 0:
        score += min(20, trending_count * 5)

    condition = str(getattr(property_obj, "property_condition", "") or "").strip().lower()
    if condition in {"excellent", "new", "renovated"}:
        score += 10
    elif condition in {"good", "fair"}:
        score += 5

    status = str(getattr(property_obj, "status", "") or "").strip().lower()
    if status == "active":
        score += 10

    return _clamp_score(score)


@log_execution
def set_customer_score(customer_id: int, score: int) -> int:
    normalized = _clamp_score(score)
    _cache_set(_customer_score_key(customer_id), normalized)
    return normalized


@log_execution
def get_customer_score(customer: Customer, now: Optional[datetime] = None) -> int:
    if not getattr(customer, "id", None):
        return calculate_customer_score(customer, now=now)
    cached = _cache_get(_customer_score_key(int(customer.id)))
    if cached is not None:
        return cached
    return set_customer_score(int(customer.id), calculate_customer_score(customer, now=now))


@log_execution
def set_property_score(property_id: int, score: int) -> int:
    normalized = _clamp_score(score)
    _cache_set(_property_score_key(property_id), normalized)
    return normalized


@log_execution
def get_property_score(
    property_obj: Property,
    neighborhood_benchmarks: Optional[Dict[str, float]] = None,
    recent_favorites_map: Optional[Dict[int, int]] = None,
) -> int:
    if not getattr(property_obj, "id", None):
        return calculate_property_score(
            property_obj,
            neighborhood_benchmarks=neighborhood_benchmarks,
            recent_favorites_map=recent_favorites_map,
        )
    cached = _cache_get(_property_score_key(int(property_obj.id)))
    if cached is not None:
        return cached
    score = calculate_property_score(
        property_obj,
        neighborhood_benchmarks=neighborhood_benchmarks,
        recent_favorites_map=recent_favorites_map,
    )
    return set_property_score(int(property_obj.id), score)


@log_execution
def customer_priority_badge(score: int) -> str:
    if score >= _HOT_LEAD_THRESHOLD:
        return "Hot Lead"
    if score >= 60:
        return "Warm Lead"
    return "Browsing"


@log_execution
def property_priority_badge(score: int) -> str:
    if score >= _RARE_FIND_THRESHOLD:
        return "Rare Find"
    if score >= 60:
        return "Top Match"
    return "Standard"


@log_execution
def compute_and_cache_scores() -> Dict[str, Any]:
    customers = Customer.query.filter(Customer.is_deleted.is_(False)).all()
    properties = Property.query.filter(Property.is_deleted.is_(False), Property.status == "active").all()

    benchmarks = build_neighborhood_price_per_sqm(properties)
    favorites_map = build_recent_favorites_map(hours=48)

    customer_scores: Dict[int, int] = {}
    for customer in customers:
        if not getattr(customer, "id", None):
            continue
        customer_scores[int(customer.id)] = set_customer_score(
            int(customer.id),
            calculate_customer_score(customer),
        )

    property_scores: Dict[int, int] = {}
    for property_obj in properties:
        if not getattr(property_obj, "id", None):
            continue
        property_scores[int(property_obj.id)] = set_property_score(
            int(property_obj.id),
            calculate_property_score(
                property_obj,
                neighborhood_benchmarks=benchmarks,
                recent_favorites_map=favorites_map,
            ),
        )

    return {
        "customers_processed": len(customer_scores),
        "properties_processed": len(property_scores),
        "hot_leads": sum(1 for score in customer_scores.values() if score >= _HOT_LEAD_THRESHOLD),
        "rare_finds": sum(1 for score in property_scores.values() if score >= _RARE_FIND_THRESHOLD),
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }


@log_execution
def _budget_match_score(customer: Customer, property_obj: Property) -> int:
    budget_min = _safe_int(getattr(customer, "budget_min", 0), default=0)
    budget_max = _safe_int(getattr(customer, "budget_max", 0), default=0)
    price = _safe_int(getattr(property_obj, "price", 0), default=0)
    if price <= 0:
        return 0
    if budget_min > 0 and budget_max > 0 and budget_min <= price <= budget_max:
        return 40
    if budget_max > 0 and price <= int(budget_max * 1.1):
        return 25
    if budget_max > 0 and price <= int(budget_max * 1.25):
        return 10
    return 0


@log_execution
def _bed_bath_match_score(customer: Customer, property_obj: Property) -> int:
    preferred_beds = _safe_int(getattr(customer, "preferred_bedrooms", 0), default=0)
    preferred_baths = _safe_int(getattr(customer, "preferred_bathrooms", 0), default=0)
    bedrooms = _safe_int(getattr(property_obj, "bedrooms", 0), default=0)
    bathrooms = _safe_int(getattr(property_obj, "bathrooms", 0), default=0)

    score = 0
    if preferred_beds <= 0:
        score += 10
    elif bedrooms >= preferred_beds:
        score += 20
    elif bedrooms == max(0, preferred_beds - 1):
        score += 10

    if preferred_baths <= 0:
        score += 5
    elif bathrooms >= preferred_baths:
        score += 10
    elif bathrooms == max(0, preferred_baths - 1):
        score += 5

    return score


@log_execution
def _type_location_match_score(customer: Customer, property_obj: Property) -> int:
    preferred_type = str(getattr(customer, "preferred_type", "") or "").strip().lower()
    property_type = str(getattr(property_obj, "property_type", "") or "").strip().lower()
    preferred_location = str(getattr(customer, "location_preference", "") or "").strip().lower()
    neighborhood = str(getattr(property_obj, "neighborhood", "") or "").strip().lower()

    score = 0
    if preferred_type:
        if preferred_type == property_type:
            score += 10
    else:
        score += 5

    if preferred_location and neighborhood:
        if neighborhood in preferred_location or preferred_location in neighborhood:
            score += 10
    elif not preferred_location:
        score += 5

    return score


@log_execution
def rank_properties_for_customer(
    customer: Customer,
    max_results: int = 3,
    min_property_score: int = 0,
) -> List[Dict[str, Any]]:
    query = Property.query.filter(Property.is_deleted.is_(False), Property.status == "active")
    if _safe_int(getattr(customer, "budget_min", 0), default=0) > 0:
        query = query.filter(Property.price >= int(customer.budget_min * 0.8))
    if _safe_int(getattr(customer, "budget_max", 0), default=0) > 0:
        query = query.filter(Property.price <= int(customer.budget_max * 1.25))

    candidates = query.order_by(Property.created_at.desc(), Property.id.desc()).limit(80).all()
    if not candidates:
        return []

    benchmarks = build_neighborhood_price_per_sqm(candidates)
    favorites_map = build_recent_favorites_map(hours=48)
    limit = max(1, min(_safe_int(max_results, default=3), 10))
    min_score = max(0, min(_safe_int(min_property_score, default=0), 100))

    ranked: List[Dict[str, Any]] = []
    for property_obj in candidates:
        property_score = get_property_score(
            property_obj,
            neighborhood_benchmarks=benchmarks,
            recent_favorites_map=favorites_map,
        )
        if property_score < min_score:
            continue

        match_score = (
            _budget_match_score(customer, property_obj)
            + _bed_bath_match_score(customer, property_obj)
            + _type_location_match_score(customer, property_obj)
            + int(round(property_score * 0.2))
        )
        match_score = _clamp_score(match_score)

        smart_context = extract_property_smart_context(property_obj)
        ranked.append(
            {
                "property": property_obj,
                "match_score": match_score,
                "property_score": property_score,
                "property_badge": property_priority_badge(property_score),
                "smart_benefits": smart_context.get("smart_benefits", []),
                "trending_badges": smart_context.get("trending_badges", []),
            }
        )

    ranked.sort(
        key=lambda row: (
            -int(row.get("match_score", 0)),
            -int(row.get("property_score", 0)),
            float(getattr(row.get("property"), "price", 0) or 0),
            int(getattr(row.get("property"), "id", 0) or 0),
        )
    )
    return ranked[:limit]


@log_execution
def build_matchmaker_pitch(customer: Customer, ranked_match: Dict[str, Any]) -> str:
    property_obj = ranked_match.get("property")
    if property_obj is None:
        return "I found no qualified match right now. I can re-run once new listings arrive."

    match_score = _safe_int(ranked_match.get("match_score"), default=0)
    first_benefit = ""
    smart_benefits = ranked_match.get("smart_benefits")
    if isinstance(smart_benefits, list) and smart_benefits:
        first = smart_benefits[0]
        if isinstance(first, dict):
            first_benefit = str(first.get("benefit") or "").strip()
        elif isinstance(first, str):
            first_benefit = first.strip()
    if not first_benefit:
        first_benefit = "This listing aligns well with your current buying profile."

    return (
        f"Hi {customer.name}, I found a strong match: {property_obj.title} "
        f"({match_score}% match) at {property_obj.address}. {first_benefit} "
        "Would you like to schedule a tour this week?"
    )

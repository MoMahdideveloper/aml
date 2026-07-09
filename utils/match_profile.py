"""Shared customer match-preference completeness for UI and APIs."""

from typing import Any, Dict, Optional


def customer_preference_profile(customer: Optional[Any]) -> Dict[str, Any]:
    """Build UI profile + completeness for recommendation matching parameters."""
    if not customer:
        return {
            "filled": 0,
            "total": 7,
            "percent": 0,
            "missing": [
                "budget",
                "bedrooms",
                "bathrooms",
                "type",
                "location",
                "features",
                "contact",
            ],
            "checks": {},
            "is_weak": True,
        }

    checks = {
        "budget": bool(
            (getattr(customer, "budget_min", 0) or 0) > 0
            or (getattr(customer, "budget_max", 0) or 0) > 0
        ),
        "bedrooms": bool((getattr(customer, "preferred_bedrooms", 0) or 0) > 0),
        "bathrooms": bool((getattr(customer, "preferred_bathrooms", 0) or 0) > 0),
        "type": bool((getattr(customer, "preferred_type", None) or "").strip()),
        "location": bool((getattr(customer, "location_preference", None) or "").strip()),
        "features": bool((getattr(customer, "preferences", None) or "").strip()),
        "contact": bool(
            (getattr(customer, "email", None) or "").strip()
            and (getattr(customer, "phone", None) or "").strip()
        ),
    }
    filled = sum(1 for ok in checks.values() if ok)
    total = len(checks)
    missing = [k for k, ok in checks.items() if not ok]
    percent = int(round(100.0 * filled / total)) if total else 0
    return {
        "filled": filled,
        "total": total,
        "percent": percent,
        "missing": missing,
        "checks": checks,
        "is_weak": percent < 50,
    }

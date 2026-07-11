"""Deterministic customer profile completeness (structured fields only)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Field key → human label (never free-text preferences)
_CHECKS = (
    ("budget_min", "Minimum budget", lambda c: int(getattr(c, "budget_min", 0) or 0) > 0),
    ("budget_max", "Maximum budget", lambda c: int(getattr(c, "budget_max", 0) or 0) > 0),
    (
        "preferred_bedrooms",
        "Preferred bedrooms",
        lambda c: int(getattr(c, "preferred_bedrooms", 0) or 0) > 0,
    ),
    (
        "preferred_bathrooms",
        "Preferred bathrooms",
        lambda c: int(getattr(c, "preferred_bathrooms", 0) or 0) > 0,
    ),
    (
        "preferred_type",
        "Preferred property type",
        lambda c: bool((getattr(c, "preferred_type", None) or "").strip()),
    ),
    (
        "location_preference",
        "Location preference",
        lambda c: bool((getattr(c, "location_preference", None) or "").strip()),
    ),
    (
        "status",
        "Lead status",
        lambda c: bool((getattr(c, "status", None) or "").strip()),
    ),
)


def evaluate_customer_completeness(customer: Any) -> Dict[str, Any]:
    """
    Return completeness summary for a Customer ORM row or duck-typed object.

    Never reads or returns free-text ``preferences``.
    """
    if customer is None:
        return {
            "complete": False,
            "score": 0.0,
            "present": [],
            "missing": [],
            "missing_labels": [],
            "total_checks": len(_CHECKS),
        }

    present: List[str] = []
    missing: List[str] = []
    missing_labels: List[str] = []
    for key, label, ok_fn in _CHECKS:
        try:
            ok = bool(ok_fn(customer))
        except Exception:
            ok = False
        if ok:
            present.append(key)
        else:
            missing.append(key)
            missing_labels.append(label)

    total = len(_CHECKS)
    score = (len(present) / float(total)) if total else 1.0
    return {
        "complete": len(missing) == 0,
        "score": round(score, 3),
        "present": present,
        "missing": missing,
        "missing_labels": missing_labels,
        "total_checks": total,
        "source": "customer_completeness.v1",
    }


def completeness_section_for_context(customer: Any) -> Dict[str, Any]:
    """Shape for ContextBuilder section with provenance-style wrappers."""
    from services.context_builder import _field
    from sqlalchemy_models import _utcnow_naive

    summary = evaluate_customer_completeness(customer)
    now = _utcnow_naive()
    return {
        "score": _field(summary["score"], "customer_completeness.score", as_of=now),
        "complete": _field(summary["complete"], "customer_completeness.complete", as_of=now),
        "missing": _field(summary["missing"], "customer_completeness.missing", as_of=now),
        "missing_labels": _field(
            summary["missing_labels"], "customer_completeness.missing_labels", as_of=now
        ),
        "present": _field(summary["present"], "customer_completeness.present", as_of=now),
        "untrusted_text": _field(False, "customer_completeness.policy", as_of=now),
    }

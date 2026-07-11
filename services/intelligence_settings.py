"""Runtime CRM intelligence feature toggles (DB singleton with env seed)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from database import db
from sqlalchemy_models import IntelligenceSettings, _utcnow_naive
from utils.observability import log_event

# Public flag catalog for admin UI (stable keys).
FLAG_CATALOG: List[Dict[str, Any]] = [
    {
        "key": "global_search",
        "env": "ENABLE_GLOBAL_SEARCH",
        "label": "Global CRM search",
        "description": "Shell search box and /search routes. Recommended ON.",
        "default": True,
        "recommended": True,
    },
    {
        "key": "vocab_enrichment",
        "env": "ENABLE_VOCAB_ENRICHMENT",
        "label": "Vocabulary synonym expand",
        "description": "Expand property search with approved synonyms/replacements. Manage terms at /admin/vocab.",
        "default": False,
        "recommended": False,
    },
    {
        "key": "vocab_occurrences",
        "env": "ENABLE_VOCAB_OCCURRENCES",
        "label": "Vocabulary occurrences index",
        "description": "Extract/index concepts from property fields for context and graph mentions. Does not rewrite descriptions.",
        "default": False,
        "recommended": False,
    },
    {
        "key": "hybrid_search",
        "env": "ENABLE_HYBRID_SEARCH",
        "label": "Hybrid / natural-language search",
        "description": "Property semantic ranking + structured filters on full /search. Falls back to keyword if embeddings unavailable.",
        "default": False,
        "recommended": False,
    },
    {
        "key": "ai_context",
        "env": "ENABLE_AI_CONTEXT",
        "label": "AI context packets",
        "description": "Allowlisted /api/context for customers, properties, deals, tasks, agents.",
        "default": False,
        "recommended": False,
    },
    {
        "key": "ai_answer",
        "env": "ENABLE_AI_ANSWER",
        "label": "Grounded AI answers",
        "description": "POST /api/context/.../answer uses context packets only. Falls back to deterministic summary if LLM is down. Requires AI context ON.",
        "default": False,
        "recommended": False,
    },
    {
        "key": "derived_edges",
        "env": "ENABLE_DERIVED_EDGES",
        "label": "Related entities graph",
        "description": "SQL relationship edges and Related panels (Customer 360 / property). Not Neo4j.",
        "default": False,
        "recommended": False,
    },
    {
        "key": "search_shadow",
        "env": "ENABLE_SEARCH_SHADOW",
        "label": "Hybrid shadow ranking",
        "description": "When hybrid is ON, compute hybrid order for metrics but keep user-visible property order as keyword. Safe staging.",
        "default": False,
        "recommended": True,
    },
    {
        "key": "description_search",
        "env": "ENABLE_DESCRIPTION_SEARCH",
        "label": "Search property descriptions",
        "description": "Include property description in global keyword search (noise/PII risk). Default OFF.",
        "default": False,
        "recommended": False,
    },
    {
        "key": "nl_query_parse",
        "env": "ENABLE_NL_QUERY_PARSE",
        "label": "Optional LLM query parse",
        "description": "Use LLM only to fill soft constraints when rules are thin. Fail-open if provider down. Never ranks results.",
        "default": False,
        "recommended": False,
    },
    {
        "key": "customer_nl_filters",
        "env": "ENABLE_CUSTOMER_NL_FILTERS",
        "label": "Customer NL structured filters",
        "description": "Parse beds/budget/type/location from customer search queries. Never searches free-text preferences. Default OFF.",
        "default": False,
        "recommended": False,
    },
    {
        "key": "activity_search",
        "env": "ENABLE_ACTIVITY_SEARCH",
        "label": "Activity search (metadata only)",
        "description": "Search customer interactions by type/outcome/id via scope=activities. Never searches body or subject. Default OFF.",
        "default": False,
        "recommended": False,
    },
]




_KEY_TO_ATTR = {f["key"]: f["key"] for f in FLAG_CATALOG}


def _env_bool(env_name: str, default: bool) -> bool:
    raw = os.environ.get(env_name)
    if raw is None or str(raw).strip() == "":
        return default
    if env_name == "ENABLE_GLOBAL_SEARCH":
        # historical: default on unless explicitly 0
        return str(raw).strip() != "0"
    return str(raw).strip() == "1"


def get_or_create_settings() -> IntelligenceSettings:
    """Singleton id=1. First create seeds from process environment."""
    row = db.session.get(IntelligenceSettings, 1)
    if row:
        return row
    row = IntelligenceSettings(
        id=1,
        global_search=_env_bool("ENABLE_GLOBAL_SEARCH", True),
        vocab_enrichment=_env_bool("ENABLE_VOCAB_ENRICHMENT", False),
        vocab_occurrences=_env_bool("ENABLE_VOCAB_OCCURRENCES", False),
        hybrid_search=_env_bool("ENABLE_HYBRID_SEARCH", False),
        ai_context=_env_bool("ENABLE_AI_CONTEXT", False),
        ai_answer=_env_bool("ENABLE_AI_ANSWER", False),
        derived_edges=_env_bool("ENABLE_DERIVED_EDGES", False),
        search_shadow=_env_bool("ENABLE_SEARCH_SHADOW", False),
        description_search=_env_bool("ENABLE_DESCRIPTION_SEARCH", False),
        nl_query_parse=_env_bool("ENABLE_NL_QUERY_PARSE", False),
        customer_nl_filters=_env_bool("ENABLE_CUSTOMER_NL_FILTERS", False),
        activity_search=_env_bool("ENABLE_ACTIVITY_SEARCH", False),
        updated_by="system",
    )



    db.session.add(row)
    db.session.commit()
    log_event("intelligence_settings_seeded", component="intelligence_settings")
    return row


def is_enabled(flag_key: str) -> bool:
    """
    Effective toggle for a flag.
    Prefer DB row when table exists; fall back to env if DB unavailable.
    In Flask TESTING mode, prefer environment (so pytest monkeypatch works).
    Set INTELLIGENCE_SETTINGS_USE_ENV=1 to force env-only (ops emergency).
    """
    attr = _KEY_TO_ATTR.get(flag_key)
    if not attr:
        return False
    meta = next((f for f in FLAG_CATALOG if f["key"] == flag_key), None)
    if not meta:
        return False

    force_env = os.environ.get("INTELLIGENCE_SETTINGS_USE_ENV", "").strip() == "1"
    testing = False
    try:
        from flask import current_app, has_app_context

        if has_app_context():
            testing = bool(current_app.config.get("TESTING"))
    except Exception:
        testing = False

    if force_env or testing:
        return _env_bool(meta["env"], bool(meta["default"]))

    try:
        row = get_or_create_settings()
        return bool(getattr(row, attr, False))
    except Exception:
        return _env_bool(meta["env"], bool(meta["default"]))



def list_flags() -> List[Dict[str, Any]]:
    row = None
    try:
        row = get_or_create_settings()
    except Exception:
        pass
    out = []
    for f in FLAG_CATALOG:
        if row is not None:
            enabled = bool(getattr(row, f["key"], f["default"]))
        else:
            enabled = _env_bool(f["env"], bool(f["default"]))
        out.append({**f, "enabled": enabled})
    return out


def update_flags(
    updates: Dict[str, bool],
    *,
    by: str = "admin",
    app=None,
) -> IntelligenceSettings:
    """Persist toggles and sync Flask app.config when provided."""
    row = get_or_create_settings()
    allowed = {f["key"] for f in FLAG_CATALOG}
    for key, val in updates.items():
        if key not in allowed:
            continue
        setattr(row, key, bool(val))
    row.updated_by = (by or "admin")[:120]
    row.updated_at = _utcnow_naive()
    db.session.commit()
    if app is not None:
        apply_to_app_config(app, row)
    log_event(
        "intelligence_settings_updated",
        component="intelligence_settings",
        by=(by or "")[:40],
        # no sensitive payload
    )
    return row


def apply_to_app_config(app, row: Optional[IntelligenceSettings] = None) -> None:
    """Mirror toggles into app.config for templates that use config.get(...)."""
    if row is None:
        try:
            row = get_or_create_settings()
        except Exception:
            return
    app.config["ENABLE_GLOBAL_SEARCH"] = bool(row.global_search)
    app.config["ENABLE_VOCAB_ENRICHMENT"] = bool(row.vocab_enrichment)
    app.config["ENABLE_VOCAB_OCCURRENCES"] = bool(row.vocab_occurrences)
    app.config["ENABLE_HYBRID_SEARCH"] = bool(row.hybrid_search)
    app.config["ENABLE_AI_CONTEXT"] = bool(row.ai_context)
    app.config["ENABLE_AI_ANSWER"] = bool(getattr(row, "ai_answer", False))
    app.config["ENABLE_DERIVED_EDGES"] = bool(row.derived_edges)
    app.config["ENABLE_SEARCH_SHADOW"] = bool(getattr(row, "search_shadow", False))
    app.config["ENABLE_DESCRIPTION_SEARCH"] = bool(
        getattr(row, "description_search", False)
    )
    app.config["ENABLE_NL_QUERY_PARSE"] = bool(getattr(row, "nl_query_parse", False))
    app.config["ENABLE_CUSTOMER_NL_FILTERS"] = bool(
        getattr(row, "customer_nl_filters", False)
    )
    app.config["ENABLE_ACTIVITY_SEARCH"] = bool(getattr(row, "activity_search", False))





def sync_app_from_db(app) -> None:
    """Call from create_app after DB is ready; safe if table missing."""
    try:
        with app.app_context():
            apply_to_app_config(app)
    except Exception:
        # leave env-based config from create_app
        pass

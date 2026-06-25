import logging
from datetime import datetime
from typing import Any, Dict

from services.proptech_scoring import compute_and_cache_scores


logger = logging.getLogger("tasks.scoring_engine")


def batch_extract_profile(text_blob: str) -> Dict[str, Any]:
    """
    Deterministic lightweight profile extraction for background scoring.
    This intentionally avoids heavy model calls inside request paths.
    """
    text = str(text_blob or "").lower()
    urgency = "high" if any(token in text for token in ("urgent", "asap", "this week", "immediately")) else "normal"
    is_real_seller = any(token in text for token in ("sell now", "must sell", "listing owner", "owner sale"))

    return {
        "is_real_seller": bool(is_real_seller),
        "urgency": urgency,
    }


def run_nightly_scoring_job() -> Dict[str, Any]:
    started_at = datetime.utcnow()
    result = compute_and_cache_scores()
    finished_at = datetime.utcnow()

    payload: Dict[str, Any] = {
        **result,
        "started_at": started_at.isoformat() + "Z",
        "finished_at": finished_at.isoformat() + "Z",
        "duration_seconds": max(0.0, (finished_at - started_at).total_seconds()),
    }
    logger.info(
        "Nightly scoring completed: customers=%s properties=%s hot_leads=%s rare_finds=%s",
        payload.get("customers_processed", 0),
        payload.get("properties_processed", 0),
        payload.get("hot_leads", 0),
        payload.get("rare_finds", 0),
    )
    return payload

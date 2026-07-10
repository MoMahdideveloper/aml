"""Atomic deal stage transition history writes."""

from __future__ import annotations

from typing import Optional

from database import db
from services.deal_pipeline import normalize_deal_status
from sqlalchemy_models import Deal, DealStageHistory, _utcnow_naive
from utils.observability import log_event

EVENT_TRANSITION = "transition"
EVENT_BASELINE = "baseline"
EVENT_CREATE = "create"


def record_stage_change(
    deal: Deal,
    *,
    from_stage: Optional[str],
    to_stage: str,
    changed_by: Optional[str] = None,
    event_type: str = EVENT_TRANSITION,
    reason_code: str = "",
) -> Optional[DealStageHistory]:
    """Write history when stage actually changes (or create/baseline events)."""
    to_n = normalize_deal_status(to_stage)
    from_n = normalize_deal_status(from_stage) if from_stage is not None else None
    if event_type == EVENT_TRANSITION and from_n == to_n:
        return None
    row = DealStageHistory(
        deal_id=deal.id,
        from_stage=from_n or "",
        to_stage=to_n,
        changed_at=_utcnow_naive(),
        changed_by=(changed_by or "")[:120],
        event_type=event_type,
        reason_code=(reason_code or "")[:64],
    )
    db.session.add(row)
    log_event(
        "deal_stage_history",
        component="deals",
        deal_id=deal.id,
        event_type=event_type,
        # no customer names
    )
    return row


def ensure_baseline_for_existing_deals(batch_size: int = 500) -> int:
    """Idempotent baseline: one baseline row per deal that has zero history."""
    from sqlalchemy import func

    count = 0
    deals = (
        Deal.query.filter(Deal.is_deleted.is_(False))
        .order_by(Deal.id.asc())
        .limit(batch_size * 10)
        .all()
    )
    for deal in deals:
        existing = (
            DealStageHistory.query.filter_by(deal_id=deal.id).count()
        )
        if existing:
            continue
        record_stage_change(
            deal,
            from_stage=None,
            to_stage=deal.status or "prospecting",
            changed_by="system:baseline",
            event_type=EVENT_BASELINE,
            reason_code="migration_baseline",
        )
        count += 1
        if count >= batch_size:
            break
    if count:
        db.session.commit()
    return count

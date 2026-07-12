"""Authorized cleanup of expired AI form audit rows and private media.

Callable service only — no background threads started from Flask app factory.
Optional Celery wiring lives in services/celery_tasks.py.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import db
from services.ai_form_assist.storage import PrivateAuditStorage, StorageError
from sqlalchemy import and_, or_
from sqlalchemy_models import (
    AIFormExtraction,
    AIFormMedia,
    AIFormReviewDecision,
    AIFormSuggestion,
    _utcnow_naive,
)
from utils.observability import log_event


DEFAULT_RETENTION_DAYS = 90


def retention_days() -> int:
    raw = (os.environ.get("AI_FORM_RETENTION_DAYS") or str(DEFAULT_RETENTION_DAYS)).strip()
    try:
        days = int(raw)
    except ValueError:
        days = DEFAULT_RETENTION_DAYS
    return max(1, min(days, 3650))


def cutoff_datetime(*, now: Optional[datetime] = None, days: Optional[int] = None) -> datetime:
    base = now or _utcnow_naive()
    return base - timedelta(days=days if days is not None else retention_days())


def list_expired_extractions(
    *,
    now: Optional[datetime] = None,
    days: Optional[int] = None,
    limit: int = 500,
) -> List[AIFormExtraction]:
    """Rows past retention by expires_at, else by created_at + retention days."""
    cutoff = cutoff_datetime(now=now, days=days)
    q = (
        AIFormExtraction.query.filter(
            or_(
                and_(
                    AIFormExtraction.expires_at.isnot(None),
                    AIFormExtraction.expires_at < cutoff,
                ),
                and_(
                    AIFormExtraction.expires_at.is_(None),
                    AIFormExtraction.created_at < cutoff,
                ),
            )
        )
        .order_by(AIFormExtraction.id.asc())
        .limit(max(1, min(limit, 5000)))
    )
    return list(q.all())


def purge_extraction(
    extraction: AIFormExtraction,
    *,
    storage: Optional[PrivateAuditStorage] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Delete media files first, then child rows, then extraction.
    Never touches Property/Customer/Deal/Task/Agent CRM tables.
    """
    store = storage or PrivateAuditStorage()
    eid = extraction.id
    form_name = extraction.form_name
    # Query media keys explicitly so bulk deletes do not fight ORM relationships.
    media_rows = AIFormMedia.query.filter_by(extraction_id=eid).all()
    media_deleted = 0
    media_missing = 0
    media_errors: List[str] = []

    for m in media_rows:
        key = (m.storage_key or "").strip()
        if not key:
            continue
        if dry_run:
            media_deleted += 1
            continue
        try:
            if store.delete(key):
                media_deleted += 1
            else:
                media_missing += 1
        except StorageError as exc:
            media_errors.append(exc.code)
            # Continue: orphaned file is better than blocking DB cleanup when path is bad

    summary = {
        "extraction_id": eid,
        "form_name": form_name,
        "media_deleted": media_deleted,
        "media_missing": media_missing,
        "media_errors": media_errors,
        "dry_run": dry_run,
    }

    if dry_run:
        return summary

    # Detach loaded parent so bulk child deletes cannot mark stale relationship state.
    try:
        db.session.expunge(extraction)
    except Exception:
        pass

    AIFormReviewDecision.query.filter_by(extraction_id=eid).delete(synchronize_session=False)
    AIFormSuggestion.query.filter_by(extraction_id=eid).delete(synchronize_session=False)
    AIFormMedia.query.filter_by(extraction_id=eid).delete(synchronize_session=False)
    AIFormExtraction.query.filter_by(id=eid).delete(synchronize_session=False)
    db.session.commit()

    log_event(
        "ai_form_retention_purged",
        component="ai_form_assist",
        extraction_id=eid,
        form_name=summary["form_name"],
        media_deleted=media_deleted,
        media_missing=media_missing,
        # no raw content, paths, or PII
    )
    return summary


def cleanup_expired_ai_form_audit(
    *,
    dry_run: bool = True,
    limit: int = 200,
    days: Optional[int] = None,
    now: Optional[datetime] = None,
    storage: Optional[PrivateAuditStorage] = None,
) -> Dict[str, Any]:
    """
    Main entry: list expired extractions and optionally purge them.

    dry_run=True (default) only reports candidates — safe for operators.
    """
    store = storage or PrivateAuditStorage()
    candidates = list_expired_extractions(now=now, days=days, limit=limit)
    results: List[Dict[str, Any]] = []
    errors = 0

    for ext in candidates:
        try:
            results.append(purge_extraction(ext, storage=store, dry_run=dry_run))
        except Exception as exc:
            errors += 1
            db.session.rollback()
            log_event(
                "ai_form_retention_error",
                component="ai_form_assist",
                extraction_id=getattr(ext, "id", None),
                error_type=type(exc).__name__,
            )
            results.append(
                {
                    "extraction_id": getattr(ext, "id", None),
                    "error": type(exc).__name__,
                    "dry_run": dry_run,
                }
            )

    report = {
        "dry_run": dry_run,
        "retention_days": days if days is not None else retention_days(),
        "candidate_count": len(candidates),
        "purged_count": 0 if dry_run else sum(1 for r in results if "error" not in r),
        "error_count": errors,
        "results": results,
    }
    log_event(
        "ai_form_retention_run",
        component="ai_form_assist",
        dry_run=dry_run,
        candidate_count=report["candidate_count"],
        purged_count=report["purged_count"],
        error_count=errors,
        retention_days=report["retention_days"],
    )
    return report

"""Customer 360 timeline: manual interactions + generated events (no note-body search)."""

from __future__ import annotations

import html
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from flask import g
from sqlalchemy import and_, func

from database import db
from services.deal_pipeline import normalize_deal_status
from sqlalchemy_models import (
    ActivityAuditLog,
    Agent,
    Customer,
    CustomerInteraction,
    Deal,
    DealStageHistory,
    Property,
    Task,
    _utcnow_naive,
)
from utils.observability import log_event, record_business_counter

INTERACTION_TYPES = frozenset({"note", "call", "email", "meeting", "other"})
OUTCOMES = frozenset(
    {"", "completed", "no_answer", "left_voicemail", "scheduled", "cancelled", "interested", "not_interested"}
)
MAX_BODY = 8000
MAX_SUBJECT = 200
PAGE_SIZE_DEFAULT = 25
PAGE_SIZE_MAX = 100


class TimelineError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _request_id() -> str:
    return str(getattr(g, "request_id", "") or "")[:64]


def _audit(
    *,
    action: str,
    customer_id: Optional[int],
    interaction_id: Optional[int],
    actor_user_id: Optional[int],
    actor_label: str,
    changed_fields: str = "",
) -> None:
    row = ActivityAuditLog(
        actor_user_id=actor_user_id,
        actor_label=(actor_label or "")[:120],
        customer_id=customer_id,
        interaction_id=interaction_id,
        action=action[:40],
        changed_fields=(changed_fields or "")[:255],
        request_id=_request_id(),
    )
    db.session.add(row)
    log_event(
        "activity_audit",
        component="customer360",
        action=action,
        customer_id=customer_id,
        interaction_id=interaction_id,
        # never body/subject/PII values
    )


@dataclass
class TimelinePage:
    items: List[Dict[str, Any]]
    next_cursor: Optional[str]
    has_more: bool
    total_estimate: Optional[int] = None


class CustomerTimelineService:
    def get_customer_or_404(self, customer_id: int) -> Customer:
        c = db.session.get(Customer, customer_id)
        if not c or c.is_deleted:
            raise TimelineError("not_found", "Customer not found")
        return c

    def create_interaction(
        self,
        *,
        customer_id: int,
        interaction_type: str,
        subject: str = "",
        body: str = "",
        outcome: str = "",
        occurred_at: Optional[datetime] = None,
        follow_up_at: Optional[datetime] = None,
        actor_user_id: Optional[int] = None,
        actor_label: str = "",
        related_deal_id: Optional[int] = None,
        related_property_id: Optional[int] = None,
        agent_id_for_task: Optional[int] = None,
        create_follow_up_task: bool = False,
    ) -> CustomerInteraction:
        self.get_customer_or_404(customer_id)
        itype = (interaction_type or "").strip().lower()
        if itype not in INTERACTION_TYPES:
            raise TimelineError("bad_type", f"Invalid interaction type: {itype}")
        subject = (subject or "").strip()[:MAX_SUBJECT]
        body = (body or "")[:MAX_BODY]
        outcome = (outcome or "").strip().lower()
        if outcome not in OUTCOMES:
            raise TimelineError("bad_outcome", "Invalid outcome")
        when = occurred_at or _utcnow_naive()
        if when > _utcnow_naive() + timedelta(minutes=5):
            raise TimelineError("future_time", "occurred_at cannot be far in the future")

        if related_deal_id:
            d = db.session.get(Deal, related_deal_id)
            if not d or d.is_deleted or d.customer_id != customer_id:
                raise TimelineError("bad_deal", "Deal not linked to this customer")
        if related_property_id:
            p = db.session.get(Property, related_property_id)
            if not p or getattr(p, "is_deleted", False):
                raise TimelineError("bad_property", "Property not found")

        row = CustomerInteraction(
            customer_id=customer_id,
            interaction_type=itype,
            subject=subject,
            body=body,
            outcome=outcome,
            occurred_at=when,
            follow_up_at=follow_up_at,
            actor_user_id=actor_user_id,
            actor_label=(actor_label or "")[:120],
            related_deal_id=related_deal_id,
            related_property_id=related_property_id,
            source="manual",
        )
        db.session.add(row)
        db.session.flush()

        task_id = None
        if create_follow_up_task and follow_up_at:
            task_id = self._ensure_follow_up_task(
                row, agent_id=agent_id_for_task, actor_label=actor_label
            )
            row.follow_up_task_id = task_id

        # Safe automation event (no body)
        try:
            from services.automation_engine import emit_event

            emit_event(
                event_type="interaction.created",
                aggregate_type="interaction",
                aggregate_id=row.id,
                context={
                    "customer_id": customer_id,
                    "interaction_id": row.id,
                    "interaction_type": itype,
                    "outcome": outcome,
                    "has_follow_up": bool(follow_up_at),
                    "agent_id": agent_id_for_task,
                },
                actor_id=actor_user_id,
                changed_fields=["interaction_type", "outcome", "follow_up_at"],
            )
        except Exception:
            pass

        _audit(
            action="interaction_created",
            customer_id=customer_id,
            interaction_id=row.id,
            actor_user_id=actor_user_id,
            actor_label=actor_label,
            changed_fields="interaction_type,subject,occurred_at",
        )
        db.session.commit()
        try:
            from services.automation_engine import process_pending_outbox

            process_pending_outbox(limit=5)
        except Exception:
            pass

        log_event(
            "interaction_created",
            component="customer360",
            interaction_type=itype,
            # no body/subject/PII
        )
        record_business_counter("crm_interactions_total", outcome=itype)
        return row

    def _ensure_follow_up_task(
        self,
        interaction: CustomerInteraction,
        *,
        agent_id: Optional[int],
        actor_label: str,
    ) -> Optional[int]:
        """Idempotent follow-up task keyed by interaction id."""
        if interaction.follow_up_task_id:
            return interaction.follow_up_task_id
        # existing task for this interaction
        existing = Task.query.filter(
            Task.is_deleted.is_(False),
            Task.automation_title_key == "interaction_followup",
            Task.source_entity_type == "interaction",
            Task.source_entity_id == interaction.id,
        ).first()
        if existing:
            return existing.id

        aid = agent_id
        if not aid:
            # pick any active agent as fallback for assignment
            ag = Agent.query.filter_by(is_deleted=False).order_by(Agent.id.asc()).first()
            aid = ag.id if ag else None
        if not aid:
            return None

        title = f"Follow up: {interaction.interaction_type}"
        if interaction.subject:
            title = f"Follow up: {interaction.subject[:80]}"
        task = Task(
            title=title[:255],
            description=f"From interaction #{interaction.id} ({interaction.interaction_type})",
            agent_id=aid,
            priority="medium",
            status="pending",
            due_date=interaction.follow_up_at,
            automation_title_key="interaction_followup",
            source_entity_type="interaction",
            source_entity_id=interaction.id,
        )
        db.session.add(task)
        db.session.flush()
        _audit(
            action="follow_up_task_created",
            customer_id=interaction.customer_id,
            interaction_id=interaction.id,
            actor_user_id=interaction.actor_user_id,
            actor_label=actor_label,
            changed_fields="follow_up_task_id",
        )
        log_event(
            "follow_up_task_created",
            component="customer360",
            interaction_id=interaction.id,
        )
        return task.id

    def update_interaction(
        self,
        interaction_id: int,
        *,
        actor_user_id: Optional[int],
        actor_label: str,
        **fields: Any,
    ) -> CustomerInteraction:
        row = db.session.get(CustomerInteraction, interaction_id)
        if not row or row.is_deleted:
            raise TimelineError("not_found", "Interaction not found")
        if row.source != "manual":
            raise TimelineError("immutable", "Generated events cannot be edited")

        changed = []
        if "subject" in fields:
            row.subject = (fields.get("subject") or "")[:MAX_SUBJECT]
            changed.append("subject")
        if "body" in fields:
            row.body = (fields.get("body") or "")[:MAX_BODY]
            changed.append("body")
        if "outcome" in fields:
            o = (fields.get("outcome") or "").strip().lower()
            if o not in OUTCOMES:
                raise TimelineError("bad_outcome", "Invalid outcome")
            row.outcome = o
            changed.append("outcome")
        if "occurred_at" in fields and fields["occurred_at"]:
            row.occurred_at = fields["occurred_at"]
            changed.append("occurred_at")
        if "follow_up_at" in fields:
            row.follow_up_at = fields["follow_up_at"]
            changed.append("follow_up_at")
        row.updated_at = _utcnow_naive()
        _audit(
            action="interaction_updated",
            customer_id=row.customer_id,
            interaction_id=row.id,
            actor_user_id=actor_user_id,
            actor_label=actor_label,
            changed_fields=",".join(changed),
        )
        db.session.commit()
        return row

    def delete_interaction(
        self,
        interaction_id: int,
        *,
        actor_user_id: Optional[int],
        actor_label: str,
    ) -> None:
        row = db.session.get(CustomerInteraction, interaction_id)
        if not row or row.is_deleted:
            raise TimelineError("not_found", "Interaction not found")
        if row.source != "manual":
            raise TimelineError("immutable", "Generated events cannot be deleted as notes")
        row.is_deleted = True
        row.deleted_at = _utcnow_naive()
        _audit(
            action="interaction_deleted",
            customer_id=row.customer_id,
            interaction_id=row.id,
            actor_user_id=actor_user_id,
            actor_label=actor_label,
            changed_fields="is_deleted",
        )
        db.session.commit()

    def build_timeline(
        self,
        customer_id: int,
        *,
        interaction_type: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = PAGE_SIZE_DEFAULT,
        include_body: bool = True,
    ) -> TimelinePage:
        t0 = time.perf_counter()
        self.get_customer_or_404(customer_id)
        limit = max(1, min(int(limit or PAGE_SIZE_DEFAULT), PAGE_SIZE_MAX))

        # Manual interactions (paginated in DB)
        q = CustomerInteraction.query.filter(
            CustomerInteraction.customer_id == customer_id,
            CustomerInteraction.is_deleted.is_(False),
        )
        if interaction_type and interaction_type in INTERACTION_TYPES:
            q = q.filter(CustomerInteraction.interaction_type == interaction_type)

        cursor_dt, cursor_id = self._parse_cursor(cursor)
        if cursor_dt is not None:
            q = q.filter(
                (CustomerInteraction.occurred_at < cursor_dt)
                | (
                    and_(
                        CustomerInteraction.occurred_at == cursor_dt,
                        CustomerInteraction.id < cursor_id,
                    )
                )
            )

        manual_rows = (
            q.order_by(
                CustomerInteraction.occurred_at.desc(),
                CustomerInteraction.id.desc(),
            )
            .limit(limit + 1)
            .all()
        )

        items: List[Dict[str, Any]] = []
        for r in manual_rows[:limit]:
            items.append(self._manual_item(r, include_body=include_body))

        # Generated events (bounded, merged only for first pages without type filter)
        if not interaction_type:
            gen = self._generated_events(customer_id, limit=limit)
            items.extend(gen)
            # deterministic sort
            items.sort(
                key=lambda x: (
                    x.get("occurred_at") or "",
                    x.get("sort_id") or 0,
                ),
                reverse=True,
            )
            items = items[:limit]

        has_more = len(manual_rows) > limit
        next_c = None
        if has_more and manual_rows:
            last = manual_rows[limit - 1] if len(manual_rows) > limit else manual_rows[-1]
            if len(manual_rows) > limit:
                last = manual_rows[limit - 1]
                next_c = self._make_cursor(last.occurred_at, last.id)

        duration_ms = int((time.perf_counter() - t0) * 1000)
        log_event(
            "timeline_viewed",
            component="customer360",
            duration_ms=duration_ms,
            result_band=self._band(len(items)),
            # no names/bodies
        )
        return TimelinePage(items=items, next_cursor=next_c, has_more=has_more)

    def _manual_item(self, r: CustomerInteraction, *, include_body: bool) -> Dict[str, Any]:
        return {
            "kind": "manual",
            "editable": True,
            "id": r.id,
            "sort_id": r.id,
            "interaction_type": r.interaction_type,
            "subject": r.subject,
            "body": r.body if include_body else None,
            "body_html": html.escape(r.body or "") if include_body else None,
            "outcome": r.outcome,
            "occurred_at": r.occurred_at.isoformat() if r.occurred_at else None,
            "follow_up_at": r.follow_up_at.isoformat() if r.follow_up_at else None,
            "actor_label": r.actor_label,
            "follow_up_task_id": r.follow_up_task_id,
            "related_deal_id": r.related_deal_id,
            "related_property_id": r.related_property_id,
        }

    def _generated_events(self, customer_id: int, *, limit: int) -> List[Dict[str, Any]]:
        """Read-only projections from authoritative sources (not editable)."""
        items: List[Dict[str, Any]] = []
        deals = (
            Deal.query.filter(
                Deal.customer_id == customer_id, Deal.is_deleted.is_(False)
            )
            .order_by(Deal.created_at.desc())
            .limit(limit)
            .all()
        )
        for d in deals:
            items.append(
                {
                    "kind": "generated",
                    "editable": False,
                    "id": f"deal-created-{d.id}",
                    "sort_id": d.id,
                    "interaction_type": "system",
                    "subject": f"Deal #{d.id} created",
                    "body": None,
                    "body_html": None,
                    "outcome": normalize_deal_status(d.status),
                    "occurred_at": d.created_at.isoformat() if d.created_at else None,
                    "actor_label": "system",
                    "related_deal_id": d.id,
                }
            )
            hist = (
                DealStageHistory.query.filter_by(deal_id=d.id, event_type="transition")
                .order_by(DealStageHistory.changed_at.desc())
                .limit(10)
                .all()
            )
            for h in hist:
                items.append(
                    {
                        "kind": "generated",
                        "editable": False,
                        "id": f"deal-stage-{h.id}",
                        "sort_id": h.id,
                        "interaction_type": "system",
                        "subject": f"Deal #{d.id}: {h.from_stage or '—'} → {h.to_stage}",
                        "body": None,
                        "body_html": None,
                        "outcome": h.to_stage,
                        "occurred_at": h.changed_at.isoformat() if h.changed_at else None,
                        "actor_label": h.changed_by or "system",
                        "related_deal_id": d.id,
                    }
                )
        # Tasks linked via interactions for this customer
        interaction_ids = [
            row[0]
            for row in db.session.query(CustomerInteraction.id)
            .filter(
                CustomerInteraction.customer_id == customer_id,
                CustomerInteraction.is_deleted.is_(False),
            )
            .limit(200)
            .all()
        ]
        if interaction_ids:
            tasks = (
                Task.query.filter(
                    Task.is_deleted.is_(False),
                    Task.source_entity_type == "interaction",
                    Task.source_entity_id.in_(interaction_ids),
                )
                .order_by(Task.created_at.desc())
                .limit(limit)
                .all()
            )
            for t in tasks:
                items.append(
                    {
                        "kind": "generated",
                        "editable": False,
                        "id": f"task-{t.id}",
                        "sort_id": t.id,
                        "interaction_type": "task",
                        "subject": t.title,
                        "body": None,
                        "body_html": None,
                        "outcome": t.status,
                        "occurred_at": t.created_at.isoformat() if t.created_at else None,
                        "actor_label": "system",
                        "follow_up_task_id": t.id,
                    }
                )
        return items

    def _parse_cursor(self, cursor: Optional[str]) -> Tuple[Optional[datetime], int]:
        if not cursor:
            return None, 0
        try:
            ts, sid = cursor.split("|", 1)
            return datetime.fromisoformat(ts), int(sid)
        except Exception:
            return None, 0

    def _make_cursor(self, dt: Optional[datetime], sid: int) -> str:
        return f"{dt.isoformat() if dt else ''}|{sid}"

    def _band(self, n: int) -> str:
        if n <= 10:
            return "0-10"
        if n <= 25:
            return "11-25"
        if n <= 50:
            return "26-50"
        return "50+"

    def engagement_metrics(
        self,
        *,
        start: datetime,
        end: datetime,
        agent_ids: Optional[List[int]] = None,
        inactive_days: int = 14,
    ) -> Dict[str, Any]:
        """Aggregate metrics for reports — no note bodies."""
        # interactions by type in period
        q = (
            db.session.query(
                CustomerInteraction.interaction_type,
                func.count(CustomerInteraction.id),
            )
            .filter(
                CustomerInteraction.is_deleted.is_(False),
                CustomerInteraction.occurred_at >= start,
                CustomerInteraction.occurred_at < end,
            )
            .group_by(CustomerInteraction.interaction_type)
        )
        by_type = {t: c for t, c in q.all()}

        # customers without contact in N days
        cutoff = _utcnow_naive() - timedelta(days=inactive_days)
        # last interaction per customer
        subq = (
            db.session.query(
                CustomerInteraction.customer_id,
                func.max(CustomerInteraction.occurred_at).label("last_at"),
            )
            .filter(CustomerInteraction.is_deleted.is_(False))
            .group_by(CustomerInteraction.customer_id)
            .subquery()
        )
        active_customers = Customer.query.filter(Customer.is_deleted.is_(False)).count()
        contacted_recent = (
            db.session.query(func.count())
            .select_from(subq)
            .filter(subq.c.last_at >= cutoff)
            .scalar()
            or 0
        )
        without_contact = max(0, active_customers - int(contacted_recent))

        # overdue follow-ups (tasks from interactions)
        now = _utcnow_naive()
        overdue_q = Task.query.filter(
            Task.is_deleted.is_(False),
            Task.automation_title_key == "interaction_followup",
            Task.status.in_(["pending", "in_progress", "overdue"]),
            Task.due_date.isnot(None),
            Task.due_date < now,
        )
        if agent_ids:
            overdue_q = overdue_q.filter(Task.agent_id.in_(agent_ids))
        overdue_followups = overdue_q.count()

        # average time to first follow-up: customer created → first interaction
        # Sample bounded
        customers = (
            Customer.query.filter(Customer.is_deleted.is_(False))
            .order_by(Customer.id.desc())
            .limit(200)
            .all()
        )
        deltas = []
        for c in customers:
            first = (
                CustomerInteraction.query.filter(
                    CustomerInteraction.customer_id == c.id,
                    CustomerInteraction.is_deleted.is_(False),
                )
                .order_by(CustomerInteraction.occurred_at.asc())
                .first()
            )
            if first and c.created_at and first.occurred_at:
                deltas.append((first.occurred_at - c.created_at).total_seconds() / 3600.0)
        avg_hours = round(sum(deltas) / len(deltas), 2) if deltas else None

        return {
            "interactions_by_type": by_type,
            "customers_without_contact": without_contact,
            "inactive_days": inactive_days,
            "overdue_followups": overdue_followups,
            "avg_hours_to_first_follow_up": avg_hours,
            "period": {"start": start.isoformat(), "end": end.isoformat()},
            "timezone": "UTC (naive timestamps)",
        }


customer_timeline_service = CustomerTimelineService()

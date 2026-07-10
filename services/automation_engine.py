"""Outbox-based constrained automation engine."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from database import db
from services.automation_schema import (
    DEFAULT_TEMPLATES,
    MESSAGE_TEXT,
    SCHEMA_VERSION,
    TITLE_TEXT,
    evaluate_conditions,
    sanitize_context,
    validate_actions,
    validate_conditions,
)
from sqlalchemy_models import (
    AgentNotification,
    AutomationOutboxEvent,
    AutomationRule,
    AutomationRun,
    AutomationSettings,
    Task,
    User,
    _utcnow_naive,
)
from utils.observability import log_event, record_business_counter

MAX_ATTEMPTS = 5


def feature_enabled() -> bool:
    if os.environ.get("ENABLE_AUTOMATION", "1").strip() == "0":
        return False
    settings = db.session.get(AutomationSettings, 1)
    if settings is not None and not settings.global_enabled:
        return False
    return True


def get_or_create_settings() -> AutomationSettings:
    s = db.session.get(AutomationSettings, 1)
    if not s:
        s = AutomationSettings(id=1, global_enabled=True, updated_by="system")
        db.session.add(s)
        db.session.flush()
    return s


def set_global_enabled(enabled: bool, by: str = "admin") -> AutomationSettings:
    s = get_or_create_settings()
    s.global_enabled = bool(enabled)
    s.updated_by = (by or "")[:120]
    s.updated_at = _utcnow_naive()
    db.session.commit()
    log_event(
        "automation_kill_switch",
        component="automation",
        enabled=bool(enabled),
    )
    return s


def emit_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: int,
    context: Optional[Dict[str, Any]] = None,
    actor_id: Optional[int] = None,
    changed_fields: Optional[List[str]] = None,
    correlation_id: str = "",
    process_inline: bool = True,
) -> Optional[AutomationOutboxEvent]:
    """Insert outbox row (caller should be in open transaction). Always emit; kill switch blocks process only."""
    safe = sanitize_context(context or {})
    safe["event_type"] = event_type
    safe["entity_type"] = aggregate_type
    eid = uuid.uuid4().hex
    fields = ",".join((changed_fields or [])[:20])
    ev = AutomationOutboxEvent(
        event_id=eid,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        actor_id=actor_id,
        occurred_at=_utcnow_naive(),
        correlation_id=(correlation_id or "")[:64],
        changed_fields=fields[:255],
        schema_version=SCHEMA_VERSION,
        context_json=json.dumps(safe, sort_keys=True),
        status="pending",
    )
    db.session.add(ev)
    log_event(
        "automation_event_emitted",
        component="automation",
        event_type=event_type,
        aggregate_type=aggregate_type,
        # no PII
    )
    return ev


def process_pending_outbox(limit: int = 50) -> int:
    if not feature_enabled():
        return 0
    rows = (
        AutomationOutboxEvent.query.filter(
            AutomationOutboxEvent.status.in_(["pending", "failed"]),
            AutomationOutboxEvent.attempts < MAX_ATTEMPTS,
        )
        .order_by(AutomationOutboxEvent.id.asc())
        .limit(limit)
        .all()
    )
    n = 0
    for row in rows:
        if _claim_and_process(row):
            n += 1
    return n


def process_event_by_id(event_id: str, *, dry_run: bool = False) -> Dict[str, Any]:
    row = AutomationOutboxEvent.query.filter_by(event_id=event_id).first()
    if not row:
        return {"status": "missing"}
    return _process_event(row, dry_run=dry_run, force=True)


def _claim_and_process(row: AutomationOutboxEvent) -> bool:
    if row.status == "processing":
        return False
    row.status = "processing"
    row.attempts = (row.attempts or 0) + 1
    db.session.commit()
    try:
        _process_event(row, dry_run=False, force=False)
        return True
    except Exception as e:
        db.session.rollback()
        row = db.session.get(AutomationOutboxEvent, row.id)
        if not row:
            return False
        row.attempts = (row.attempts or 0) + 1
        row.last_error = str(e)[:250]
        if row.attempts >= MAX_ATTEMPTS:
            row.status = "dead"
        else:
            row.status = "failed"
        db.session.commit()
        log_event(
            "automation_event_failed",
            component="automation",
            failure_category="internal",
            attempts=row.attempts,
        )
        return False


def _process_event(
    row: AutomationOutboxEvent, *, dry_run: bool, force: bool
) -> Dict[str, Any]:
    if not feature_enabled() and not dry_run:
        row.status = "pending"
        db.session.commit()
        return {"status": "kill_switch"}

    try:
        ctx = json.loads(row.context_json or "{}")
    except json.JSONDecodeError:
        ctx = {}
    ctx = sanitize_context(ctx)
    ctx["event_type"] = row.event_type
    ctx["entity_type"] = row.aggregate_type
    if row.aggregate_type == "deal":
        ctx["deal_id"] = row.aggregate_id
    elif row.aggregate_type == "customer":
        ctx["customer_id"] = row.aggregate_id
    elif row.aggregate_type == "task":
        ctx["task_id"] = row.aggregate_id

    rules = (
        AutomationRule.query.filter_by(trigger_type=row.event_type, enabled=True)
        .order_by(AutomationRule.priority.asc(), AutomationRule.id.asc())
        .all()
    )
    results = []
    for rule in rules:
        cond = {}
        try:
            cond = validate_conditions(json.loads(rule.conditions or "{}"))
        except Exception:
            cond = json.loads(rule.conditions or "{}") if rule.conditions else {}
        matched, reason = evaluate_conditions(cond, ctx)
        if not matched:
            results.append({"rule_id": rule.id, "status": "skipped", "reason": reason})
            continue
        sup_reason = _suppression_reason(rule, row, ctx)
        if sup_reason:
            _record_run(
                rule,
                row,
                status="suppressed",
                reason=sup_reason,
                action_type="",
                dry_run=dry_run,
            )
            results.append({"rule_id": rule.id, "status": "suppressed", "reason": sup_reason})
            continue
        actions = []
        try:
            actions = validate_actions(json.loads(rule.actions or "[]"))
        except Exception:
            actions = json.loads(rule.actions or "[]")
        for action in actions:
            key = f"{rule.id}:{row.event_id}:{action.get('type')}"
            existing = AutomationRun.query.filter_by(idempotency_key=key).first()
            if existing and existing.status == "succeeded" and not dry_run:
                results.append({"rule_id": rule.id, "status": "idempotent_skip"})
                continue
            if dry_run:
                _record_run(
                    rule,
                    row,
                    status="matched",
                    reason="dry_run",
                    action_type=action.get("type", ""),
                    dry_run=True,
                    idem_key=key + ":dry",
                )
                results.append({"rule_id": rule.id, "status": "dry_run_match", "action": action.get("type")})
                continue
            try:
                ref = _execute_action(rule, row, action, ctx)
                _record_run(
                    rule,
                    row,
                    status="succeeded",
                    reason="ok",
                    action_type=action.get("type", ""),
                    action_ref=ref,
                    dry_run=False,
                    idem_key=key,
                )
                results.append({"rule_id": rule.id, "status": "succeeded", "ref": ref})
                record_business_counter("crm_automation_actions", outcome="ok")
            except Exception as e:
                _record_run(
                    rule,
                    row,
                    status="failed",
                    reason=type(e).__name__,
                    action_type=action.get("type", ""),
                    dry_run=False,
                    idem_key=key + f":fail{row.attempts}",
                    failure=type(e).__name__,
                )
                results.append({"rule_id": rule.id, "status": "failed"})

    if not dry_run:
        row.status = "processed"
        row.processed_at = _utcnow_naive()
        row.last_error = ""
        db.session.commit()
    return {"status": "processed", "results": results}


def _suppression_reason(
    rule: AutomationRule, row: AutomationOutboxEvent, ctx: Dict[str, Any]
) -> str:
    if not rule.enabled:
        return "rule_disabled"
    # cooldown
    hours = int(rule.cooldown_hours or 0)
    if hours > 0:
        since = _utcnow_naive() - timedelta(hours=hours)
        recent = (
            AutomationRun.query.filter(
                AutomationRun.rule_id == rule.id,
                AutomationRun.status == "succeeded",
                AutomationRun.started_at >= since,
            )
            .order_by(AutomationRun.id.desc())
            .limit(20)
            .all()
        )
        for r in recent:
            if r.event_id == row.event_id:
                continue
            # same aggregate via action_ref or scan of event
            ev = AutomationOutboxEvent.query.filter_by(event_id=r.event_id).first()
            if ev and ev.aggregate_type == row.aggregate_type and ev.aggregate_id == row.aggregate_id:
                return "cooldown"
    # closed deal: skip create/notify for closed aggregates on non-close events
    if row.aggregate_type == "deal" and row.event_type not in (
        "deal.closed",
        "deal.stage_changed",
    ):
        from sqlalchemy_models import Deal
        from services.deal_pipeline import TERMINAL_STAGES, normalize_deal_status

        d = db.session.get(Deal, row.aggregate_id)
        if d and (d.is_deleted or normalize_deal_status(d.status) in TERMINAL_STAGES):
            return "deal_closed_or_deleted"
    if row.aggregate_type == "customer":
        from sqlalchemy_models import Customer

        c = db.session.get(Customer, row.aggregate_id)
        if c and c.is_deleted:
            return "entity_deleted"
    return ""


def _record_run(
    rule: AutomationRule,
    row: AutomationOutboxEvent,
    *,
    status: str,
    reason: str,
    action_type: str,
    dry_run: bool = False,
    action_ref: str = "",
    idem_key: Optional[str] = None,
    failure: Optional[str] = None,
) -> AutomationRun:
    key = idem_key or f"{rule.id}:{row.event_id}:{action_type}:{status}:{uuid.uuid4().hex[:8]}"
    existing = AutomationRun.query.filter_by(idempotency_key=key).first()
    if existing:
        return existing
    run = AutomationRun(
        rule_id=rule.id,
        rule_version=rule.version or 1,
        event_id=row.event_id,
        status=status,
        reason_code=reason[:64],
        action_type=action_type[:40],
        action_ref=action_ref[:120],
        idempotency_key=key[:160],
        dry_run=dry_run,
        completed_at=_utcnow_naive(),
        failure_category=failure,
    )
    db.session.add(run)
    db.session.flush()
    return run


def _execute_action(
    rule: AutomationRule,
    row: AutomationOutboxEvent,
    action: Dict[str, Any],
    ctx: Dict[str, Any],
) -> str:
    t = action["type"]
    if t == "create_task":
        return _action_create_task(rule, row, action, ctx)
    if t == "notify":
        return _action_notify(rule, action, ctx, escalate=False)
    if t == "escalate":
        return _action_notify(rule, action, ctx, escalate=True)
    if t == "cancel_automation_tasks":
        return _action_cancel(rule, row, action)
    raise ValueError(f"unknown action {t}")


def _resolve_agent(action: Dict[str, Any], ctx: Dict[str, Any], row: AutomationOutboxEvent) -> Optional[int]:
    src = action.get("assignee") or "deal_agent"
    if src == "context_agent" and ctx.get("agent_id"):
        return int(ctx["agent_id"])
    if row.aggregate_type == "deal":
        from sqlalchemy_models import Deal

        d = db.session.get(Deal, row.aggregate_id)
        if d and d.agent_id:
            return int(d.agent_id)
    if ctx.get("agent_id"):
        return int(ctx["agent_id"])
    return None


def _action_create_task(rule, row, action, ctx) -> str:
    agent_id = _resolve_agent(action, ctx, row)
    if not agent_id:
        raise ValueError("missing_assignee")
    title_key = action.get("title_key") or "contact_new_customer"
    title = TITLE_TEXT.get(title_key, "Automated follow-up")
    existing = Task.query.filter(
        Task.is_deleted.is_(False),
        Task.status.in_(["pending", "in_progress", "overdue"]),
        Task.automation_rule_id == rule.id,
        Task.source_entity_type == row.aggregate_type,
        Task.source_entity_id == row.aggregate_id,
        Task.automation_title_key == title_key,
    ).first()
    if existing:
        return f"task:{existing.id}:exists"
    due = _utcnow_naive() + timedelta(days=int(action.get("due_days") or 1))
    task = Task(
        title=title[:255],
        description=MESSAGE_TEXT.get(title_key, "Created by automation")[:2000],
        agent_id=agent_id,
        priority=str(action.get("priority") or "medium")[:20],
        status="pending",
        due_date=due,
        automation_rule_id=rule.id,
        automation_title_key=title_key,
        source_entity_type=row.aggregate_type,
        source_entity_id=row.aggregate_id,
    )
    db.session.add(task)
    db.session.flush()
    return f"task:{task.id}"


def _action_notify(rule, action, ctx, escalate: bool) -> str:
    title_key = action.get("title_key") or "escalation"
    msg_key = action.get("message_key") or title_key
    title = TITLE_TEXT.get(title_key, "Automation")
    message = MESSAGE_TEXT.get(msg_key, "Automation notification")
    recipients: List[int] = []

    def _add(aid: Optional[int]) -> None:
        if aid and int(aid) not in recipients:
            recipients.append(int(aid))

    _add(ctx.get("agent_id"))
    if ctx.get("deal_id"):
        from sqlalchemy_models import Deal

        d = db.session.get(Deal, int(ctx["deal_id"]))
        if d:
            _add(d.agent_id)
    if ctx.get("task_id"):
        t = db.session.get(Task, int(ctx["task_id"]))
        if t:
            _add(t.agent_id)
    if escalate:
        from sqlalchemy_models import Agent

        for m in (
            Agent.query.filter(
                Agent.is_deleted.is_(False), Agent.specialization.ilike("%manager%")
            )
            .limit(5)
            .all()
        ):
            _add(m.id)
    if not recipients:
        raise ValueError("missing_assignee")
    refs = []
    for rid in recipients:
        n = AgentNotification(
            agent_id=rid,
            title=title[:200],
            message=message[:1000],
            notification_type="system",
            priority=str(action.get("priority") or "normal")[:20],
        )
        db.session.add(n)
        db.session.flush()
        refs.append(f"notif:{n.id}")
    return ",".join(refs)


def _action_cancel(rule, row, action) -> str:
    keys = action.get("match_title_keys") or []
    q = Task.query.filter(
        Task.is_deleted.is_(False),
        Task.status.in_(["pending", "in_progress", "overdue"]),
        Task.automation_rule_id.isnot(None),
        Task.source_entity_type == row.aggregate_type,
        Task.source_entity_id == row.aggregate_id,
    )
    cancelled = 0
    for task in q.all():
        if keys and task.automation_title_key not in keys:
            continue
        task.status = "cancelled"
        cancelled += 1
    return f"cancelled:{cancelled}"


def seed_disabled_templates() -> int:
    created = 0
    for tpl in DEFAULT_TEMPLATES:
        existing = AutomationRule.query.filter_by(rule_key=tpl["rule_key"]).first()
        if existing:
            continue
        # unique name constraint
        if AutomationRule.query.filter_by(name=tpl["name"]).first():
            continue
        cond = validate_conditions(tpl["conditions"])
        acts = validate_actions(tpl["actions"])
        rule = AutomationRule(
            name=tpl["name"],
            trigger_type=tpl["event_type"],
            enabled=False,  # never auto-enable
            conditions=json.dumps(cond, sort_keys=True),
            actions=json.dumps(acts, sort_keys=True),
            created_by="system:template",
            rule_key=tpl["rule_key"],
            cooldown_hours=int(tpl.get("cooldown_hours") or 24),
            priority=100,
            version=1,
            is_template=True,
        )
        db.session.add(rule)
        created += 1
    if created:
        db.session.commit()
    return created


def dry_run_rule(rule_id: int, limit: int = 20) -> Dict[str, Any]:
    rule = db.session.get(AutomationRule, rule_id)
    if not rule:
        raise ValueError("Rule not found")
    events = (
        AutomationOutboxEvent.query.filter_by(event_type=rule.trigger_type)
        .order_by(AutomationOutboxEvent.id.desc())
        .limit(limit)
        .all()
    )
    matches = []
    cond = validate_conditions(json.loads(rule.conditions or "{}"))
    for ev in events:
        ctx = sanitize_context(json.loads(ev.context_json or "{}"))
        ctx["event_type"] = ev.event_type
        ok, reason = evaluate_conditions(cond, ctx)
        if ok:
            matches.append(
                {
                    "event_id": ev.event_id,
                    "aggregate_type": ev.aggregate_type,
                    "aggregate_id": ev.aggregate_id,
                    "reason": reason,
                }
            )
    return {
        "rule_id": rule_id,
        "scanned": len(events),
        "match_count": len(matches),
        "matches": matches[:10],
        "note": "Preview performs no writes; later data may change results.",
    }


# --- Scanners ---

def scan_overdue_tasks(limit: int = 100) -> int:
    if not feature_enabled():
        return 0
    now = _utcnow_naive()
    tasks = (
        Task.query.filter(
            Task.is_deleted.is_(False),
            Task.status.in_(["pending", "in_progress", "overdue"]),
            Task.due_date.isnot(None),
            Task.due_date < now,
        )
        .limit(limit)
        .all()
    )
    n = 0
    for t in tasks:
        emit_event(
            event_type="scan.overdue_tasks",
            aggregate_type="task",
            aggregate_id=t.id,
            context={
                "task_id": t.id,
                "agent_id": t.agent_id,
                "task_overdue": True,
                "status": t.status,
                "priority": t.priority,
            },
            process_inline=False,
        )
        n += 1
    db.session.commit()
    process_pending_outbox(limit=n + 10)
    return n


def scan_inactive_deals(inactive_days: int = 7, limit: int = 100) -> int:
    if not feature_enabled():
        return 0
    from services.deal_pipeline import OPEN_STAGES, normalize_deal_status
    from sqlalchemy_models import Deal

    cutoff = _utcnow_naive() - timedelta(days=inactive_days)
    deals = (
        Deal.query.filter(Deal.is_deleted.is_(False))
        .order_by(Deal.id.asc())
        .limit(limit * 3)
        .all()
    )
    n = 0
    for d in deals:
        if normalize_deal_status(d.status) not in OPEN_STAGES:
            continue
        ts = d.updated_at or d.created_at
        if not ts or ts > cutoff:
            continue
        days = max(0, int((_utcnow_naive() - ts).total_seconds() // 86400))
        emit_event(
            event_type="scan.inactive_deals",
            aggregate_type="deal",
            aggregate_id=d.id,
            context={
                "deal_id": d.id,
                "agent_id": d.agent_id,
                "stage": normalize_deal_status(d.status),
                "offer_amount": d.offer_amount or 0,
                "inactive_days": days,
            },
            process_inline=False,
        )
        n += 1
        if n >= limit:
            break
    db.session.commit()
    process_pending_outbox(limit=n + 10)
    return n


def scan_high_value_stalled(
    min_amount: int = 5_000_000_000, inactive_days: int = 5, limit: int = 50
) -> int:
    if not feature_enabled():
        return 0
    from services.deal_pipeline import OPEN_STAGES, normalize_deal_status
    from sqlalchemy_models import Deal

    cutoff = _utcnow_naive() - timedelta(days=inactive_days)
    deals = Deal.query.filter(
        Deal.is_deleted.is_(False), Deal.offer_amount >= min_amount
    ).limit(limit * 2).all()
    n = 0
    for d in deals:
        if normalize_deal_status(d.status) not in OPEN_STAGES:
            continue
        ts = d.updated_at or d.created_at
        if not ts or ts > cutoff:
            continue
        days = max(0, int((_utcnow_naive() - ts).total_seconds() // 86400))
        emit_event(
            event_type="scan.high_value_stalled",
            aggregate_type="deal",
            aggregate_id=d.id,
            context={
                "deal_id": d.id,
                "agent_id": d.agent_id,
                "stage": normalize_deal_status(d.status),
                "offer_amount": d.offer_amount or 0,
                "inactive_days": days,
            },
            process_inline=False,
        )
        n += 1
        if n >= limit:
            break
    db.session.commit()
    process_pending_outbox(limit=n + 10)
    return n


automation_engine = type("AE", (), {})()  # namespace marker

"""Constrained automation vocabulary — no code/SQL/webhooks."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Set, Tuple

EVENT_TYPES = frozenset(
    {
        "customer.created",
        "deal.created",
        "deal.stage_changed",
        "deal.closed",
        "task.completed",
        "task.cancelled",
        "scan.inactive_deals",
        "scan.overdue_tasks",
        "scan.high_value_stalled",
        "interaction.created",
    }
)

CONDITION_KEYS = frozenset(
    {
        "event_type",
        "stage",
        "stage_in",
        "min_offer_amount",
        "max_offer_amount",
        "inactive_days_min",
        "task_overdue",
        "entity_type",
        "assignee_present",
        "interaction_type",
        "outcome",
        "has_follow_up",
    }
)

ACTION_TYPES = frozenset(
    {"create_task", "notify", "cancel_automation_tasks", "escalate"}
)

TITLE_KEYS = frozenset(
    {
        "contact_new_customer",
        "prepare_viewing",
        "negotiation_followup",
        "stale_deal_reminder",
        "overdue_task_reminder",
        "high_value_stalled",
        "escalation",
        "interaction_followup",
        "call_no_answer_followup",
    }
)

TITLE_TEXT = {
    "contact_new_customer": "Follow up with new customer",
    "prepare_viewing": "Prepare for property viewing",
    "negotiation_followup": "Negotiation follow-up",
    "stale_deal_reminder": "Stale deal needs attention",
    "overdue_task_reminder": "Overdue task reminder",
    "high_value_stalled": "High-value deal stalled",
    "escalation": "Escalation: needs manager attention",
    "interaction_followup": "Customer interaction follow-up",
    "call_no_answer_followup": "Call again — no answer",
}

MESSAGE_TEXT = {
    "contact_new_customer": "A new customer was created without an open follow-up task.",
    "prepare_viewing": "Deal entered viewing stage — prepare materials.",
    "negotiation_followup": "Deal entered negotiation — schedule follow-up.",
    "stale_deal_reminder": "Deal has been inactive beyond the threshold.",
    "overdue_task_reminder": "A task is past its due date.",
    "high_value_stalled": "High-value deal has not progressed.",
    "escalation": "Escalated automation alert.",
    "interaction_followup": "Follow up on a logged customer interaction.",
    "call_no_answer_followup": "Call outcome was no answer; schedule another attempt.",
}

CONTEXT_ALLOW = frozenset(
    {
        "agent_id",
        "customer_id",
        "deal_id",
        "task_id",
        "stage",
        "old_stage",
        "offer_amount",
        "inactive_days",
        "priority",
        "status",
        "entity_type",
        "interaction_id",
        "interaction_type",
        "outcome",
        "has_follow_up",
    }
)

MAX_JSON = 4000
SCHEMA_VERSION = 1


class RuleSchemaError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_conditions(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise RuleSchemaError("bad_conditions", "Conditions must be an object")
    out: Dict[str, Any] = {}
    for k, v in raw.items():
        if k not in CONDITION_KEYS:
            raise RuleSchemaError("unknown_condition", f"Unknown condition: {k}")
        if k == "stage_in":
            if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                raise RuleSchemaError("bad_stage_in", "stage_in must be string list")
            out[k] = [str(x)[:50] for x in v[:20]]
        elif k in ("min_offer_amount", "max_offer_amount", "inactive_days_min"):
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                raise RuleSchemaError("bad_number", f"{k} must be int") from None
        elif k == "task_overdue":
            out[k] = bool(v)
        elif k == "assignee_present":
            out[k] = bool(v)
        else:
            out[k] = str(v)[:80]
    blob = json.dumps(out, sort_keys=True)
    if len(blob) > MAX_JSON:
        raise RuleSchemaError("too_large", "Conditions too large")
    return out


def validate_actions(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise RuleSchemaError("bad_actions", "Actions must be a non-empty list")
    if len(raw) > 5:
        raise RuleSchemaError("too_many_actions", "Max 5 actions")
    out: List[Dict[str, Any]] = []
    for a in raw:
        if not isinstance(a, dict):
            raise RuleSchemaError("bad_action", "Each action must be object")
        t = a.get("type")
        if t not in ACTION_TYPES:
            raise RuleSchemaError("unknown_action", f"Unknown action type: {t}")
        item: Dict[str, Any] = {"type": t}
        if t == "create_task":
            tk = a.get("title_key") or "contact_new_customer"
            if tk not in TITLE_KEYS:
                raise RuleSchemaError("bad_title_key", f"Invalid title_key: {tk}")
            item["title_key"] = tk
            item["due_days"] = int(a.get("due_days") or 1)
            if item["due_days"] < 0 or item["due_days"] > 90:
                raise RuleSchemaError("bad_due_days", "due_days 0..90")
            item["priority"] = str(a.get("priority") or "medium")[:20]
            item["assignee"] = str(a.get("assignee") or "deal_agent")[:32]
            if item["assignee"] not in ("deal_agent", "context_agent"):
                raise RuleSchemaError("bad_assignee", "Invalid assignee source")
        elif t in ("notify", "escalate"):
            tk = a.get("title_key") or "escalation"
            mk = a.get("message_key") or tk
            if tk not in TITLE_KEYS or mk not in MESSAGE_TEXT:
                raise RuleSchemaError("bad_keys", "Invalid title/message key")
            item["title_key"] = tk
            item["message_key"] = mk
            item["priority"] = str(a.get("priority") or "normal")[:20]
        elif t == "cancel_automation_tasks":
            keys = a.get("match_title_keys") or []
            if not isinstance(keys, list):
                raise RuleSchemaError("bad_cancel", "match_title_keys list required")
            item["match_title_keys"] = [str(x)[:40] for x in keys[:10] if x in TITLE_KEYS]
        out.append(item)
    blob = json.dumps(out, sort_keys=True)
    if len(blob) > MAX_JSON:
        raise RuleSchemaError("too_large", "Actions too large")
    return out


def sanitize_context(ctx: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in (ctx or {}).items():
        if k not in CONTEXT_ALLOW:
            continue
        if isinstance(v, (int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = str(v)[:120]
    return out


def evaluate_conditions(conditions: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, str]:
    """Pure evaluator — no writes. Missing required fields fail closed."""
    if not conditions:
        return True, "empty_match"
    for key, expected in conditions.items():
        if key == "event_type":
            if context.get("event_type") != expected:
                return False, "event_type_mismatch"
        elif key == "stage":
            if context.get("stage") != expected:
                return False, "stage_mismatch"
        elif key == "stage_in":
            if context.get("stage") not in expected:
                return False, "stage_not_in"
        elif key == "min_offer_amount":
            amt = context.get("offer_amount")
            if amt is None or int(amt) < int(expected):
                return False, "offer_too_low"
        elif key == "max_offer_amount":
            amt = context.get("offer_amount")
            if amt is None or int(amt) > int(expected):
                return False, "offer_too_high"
        elif key == "inactive_days_min":
            days = context.get("inactive_days")
            if days is None or int(days) < int(expected):
                return False, "not_inactive_enough"
        elif key == "task_overdue":
            if bool(context.get("task_overdue")) != bool(expected):
                return False, "overdue_mismatch"
        elif key == "entity_type":
            if context.get("entity_type") != expected:
                return False, "entity_mismatch"
        elif key == "assignee_present":
            has = context.get("agent_id") is not None
            if has != bool(expected):
                return False, "assignee_mismatch"
        elif key == "interaction_type":
            if context.get("interaction_type") != expected:
                return False, "interaction_type_mismatch"
        elif key == "outcome":
            if context.get("outcome") != expected:
                return False, "outcome_mismatch"
        elif key == "has_follow_up":
            if bool(context.get("has_follow_up")) != bool(expected):
                return False, "follow_up_mismatch"
        else:
            return False, "unknown_condition"
    return True, "matched"


DEFAULT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "name": "New customer follow-up",
        "rule_key": "tpl_new_customer_followup",
        "event_type": "customer.created",
        "conditions": {"event_type": "customer.created", "assignee_present": True},
        "actions": [
            {
                "type": "create_task",
                "title_key": "contact_new_customer",
                "due_days": 1,
                "priority": "high",
                "assignee": "context_agent",
            }
        ],
        "cooldown_hours": 24,
    },
    {
        "name": "Viewing preparation",
        "rule_key": "tpl_viewing_prep",
        "event_type": "deal.stage_changed",
        "conditions": {
            "event_type": "deal.stage_changed",
            "stage": "property_shown",
            "assignee_present": True,
        },
        "actions": [
            {
                "type": "create_task",
                "title_key": "prepare_viewing",
                "due_days": 1,
                "priority": "high",
                "assignee": "deal_agent",
            }
        ],
        "cooldown_hours": 12,
    },
    {
        "name": "Negotiation follow-up",
        "rule_key": "tpl_negotiation_followup",
        "event_type": "deal.stage_changed",
        "conditions": {
            "event_type": "deal.stage_changed",
            "stage": "negotiation",
            "assignee_present": True,
        },
        "actions": [
            {
                "type": "create_task",
                "title_key": "negotiation_followup",
                "due_days": 2,
                "priority": "high",
                "assignee": "deal_agent",
            }
        ],
        "cooldown_hours": 12,
    },
    {
        "name": "Stale deal reminder",
        "rule_key": "tpl_stale_deal",
        "event_type": "scan.inactive_deals",
        "conditions": {
            "event_type": "scan.inactive_deals",
            "inactive_days_min": 7,
            "assignee_present": True,
        },
        "actions": [
            {
                "type": "notify",
                "title_key": "stale_deal_reminder",
                "message_key": "stale_deal_reminder",
                "priority": "normal",
            }
        ],
        "cooldown_hours": 72,
    },
    {
        "name": "Overdue task reminder",
        "rule_key": "tpl_overdue_task",
        "event_type": "scan.overdue_tasks",
        "conditions": {"event_type": "scan.overdue_tasks", "task_overdue": True},
        "actions": [
            {
                "type": "notify",
                "title_key": "overdue_task_reminder",
                "message_key": "overdue_task_reminder",
                "priority": "high",
            }
        ],
        "cooldown_hours": 24,
    },
    {
        "name": "High-value stalled escalation",
        "rule_key": "tpl_high_value_stalled",
        "event_type": "scan.high_value_stalled",
        "conditions": {
            "event_type": "scan.high_value_stalled",
            "min_offer_amount": 5_000_000_000,
            "inactive_days_min": 5,
        },
        "actions": [
            {
                "type": "escalate",
                "title_key": "high_value_stalled",
                "message_key": "high_value_stalled",
                "priority": "high",
            }
        ],
        "cooldown_hours": 48,
    },
    {
        "name": "Close deal cleanup",
        "rule_key": "tpl_close_deal_cleanup",
        "event_type": "deal.closed",
        "conditions": {"event_type": "deal.closed"},
        "actions": [
            {
                "type": "cancel_automation_tasks",
                "match_title_keys": [
                    "prepare_viewing",
                    "negotiation_followup",
                    "stale_deal_reminder",
                ],
            }
        ],
        "cooldown_hours": 0,
    },
    {
        "name": "Call no-answer follow-up",
        "rule_key": "tpl_call_no_answer",
        "event_type": "interaction.created",
        "conditions": {
            "event_type": "interaction.created",
            "interaction_type": "call",
            "outcome": "no_answer",
            "has_follow_up": True,
        },
        "actions": [
            {
                "type": "create_task",
                "title_key": "call_no_answer_followup",
                "due_days": 1,
                "priority": "high",
                "assignee": "context_agent",
            }
        ],
        "cooldown_hours": 0,
    },
]

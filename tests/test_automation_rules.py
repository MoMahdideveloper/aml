"""Rule schema validation and templates."""

import pytest
from services.automation_schema import (
    DEFAULT_TEMPLATES,
    RuleSchemaError,
    evaluate_conditions,
    validate_actions,
    validate_conditions,
)
from services.automation_engine import seed_disabled_templates
from sqlalchemy_models import AutomationRule


def test_reject_unknown_condition():
    with pytest.raises(RuleSchemaError):
        validate_conditions({"sql": "drop"})


def test_reject_unknown_action():
    with pytest.raises(RuleSchemaError):
        validate_actions([{"type": "run_shell", "cmd": "x"}])


def test_validate_create_task_action():
    acts = validate_actions(
        [
            {
                "type": "create_task",
                "title_key": "contact_new_customer",
                "due_days": 2,
                "priority": "high",
                "assignee": "deal_agent",
            }
        ]
    )
    assert acts[0]["type"] == "create_task"


def test_evaluate_stage_match():
    ok, reason = evaluate_conditions(
        {"stage": "negotiation"}, {"stage": "negotiation", "event_type": "deal.stage_changed"}
    )
    assert ok and reason == "matched"
    ok2, r2 = evaluate_conditions({"stage": "negotiation"}, {"stage": "prospecting"})
    assert not ok2


def test_seed_templates_disabled(db_setup, app):
    with app.app_context():
        n = seed_disabled_templates()
        assert n == len(DEFAULT_TEMPLATES)
        n2 = seed_disabled_templates()
        assert n2 == 0
        rules = AutomationRule.query.filter_by(is_template=True).all()
        assert all(not r.enabled for r in rules)

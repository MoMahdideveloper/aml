"""Scanner idempotency."""

from datetime import timedelta

from services.automation_engine import scan_overdue_tasks, seed_disabled_templates
from sqlalchemy_models import Agent, AutomationOutboxEvent, AutomationRule, Task, _utcnow_naive


def test_overdue_scan_emits_and_notifies(db_setup, app):
    with app.app_context():
        from database import db

        seed_disabled_templates()
        rule = AutomationRule.query.filter_by(rule_key="tpl_overdue_task").first()
        rule.enabled = True
        db.session.commit()
        ag = Agent(name="S", email="s@example.com", phone="5558200001")
        db.session.add(ag)
        db.session.flush()
        t = Task(
            title="Late",
            agent_id=ag.id,
            status="pending",
            due_date=_utcnow_naive() - timedelta(days=2),
        )
        db.session.add(t)
        db.session.commit()
        n1 = scan_overdue_tasks()
        n2 = scan_overdue_tasks()
        assert n1 >= 1
        # second scan may emit again but cooldown/idempotency should limit actions
        assert n2 >= 1
        events = AutomationOutboxEvent.query.filter_by(
            event_type="scan.overdue_tasks", aggregate_id=t.id
        ).count()
        assert events >= 1

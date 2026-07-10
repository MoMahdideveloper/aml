"""Executor idempotency, kill switch, actions."""

import json

from database_service import database_service
from services.automation_engine import (
    process_pending_outbox,
    seed_disabled_templates,
    set_global_enabled,
)
from services.automation_schema import validate_actions, validate_conditions
from sqlalchemy_models import (
    Agent,
    AgentNotification,
    AutomationOutboxEvent,
    AutomationRule,
    Customer,
    Property,
    Task,
)


def _enable_viewing_rule(db):
    seed_disabled_templates()
    rule = AutomationRule.query.filter_by(rule_key="tpl_viewing_prep").first()
    rule.enabled = True
    db.session.commit()
    return rule


def test_stage_change_creates_one_task(db_setup, app):
    with app.app_context():
        from database import db

        p = Property(title="V", address="3", property_type="apt", price=1)
        c = Customer(name="Cv", email="v@example.com", phone="5558100001")
        ag = Agent(name="Avg", email="avg@example.com", phone="5558100002")
        db.session.add_all([p, c, ag])
        db.session.commit()
        _enable_viewing_rule(db)
        d = database_service.add_deal(p.id, c.id, ag.id, "prospecting", 1000)
        database_service.update_deal(d.id, status="property_shown")
        tasks = Task.query.filter_by(
            automation_title_key="prepare_viewing", source_entity_id=d.id
        ).all()
        assert len(tasks) == 1
        # replay process does not duplicate
        process_pending_outbox(limit=20)
        assert (
            Task.query.filter_by(
                automation_title_key="prepare_viewing", source_entity_id=d.id
            ).count()
            == 1
        )


def test_kill_switch_blocks_new_actions(db_setup, app):
    with app.app_context():
        from database import db

        p = Property(title="K", address="4", property_type="apt", price=1)
        c = Customer(name="Ck", email="k@example.com", phone="5558100003")
        ag = Agent(name="Akg", email="akg@example.com", phone="5558100004")
        db.session.add_all([p, c, ag])
        db.session.commit()
        _enable_viewing_rule(db)
        set_global_enabled(False, by="test")
        d = database_service.add_deal(p.id, c.id, ag.id, "prospecting", 1000)
        database_service.update_deal(d.id, status="property_shown")
        assert (
            Task.query.filter_by(
                automation_title_key="prepare_viewing", source_entity_id=d.id
            ).count()
            == 0
        )
        set_global_enabled(True, by="test")


def test_close_cancels_automation_tasks(db_setup, app):
    with app.app_context():
        from database import db

        seed_disabled_templates()
        for key in ("tpl_viewing_prep", "tpl_close_deal_cleanup"):
            r = AutomationRule.query.filter_by(rule_key=key).first()
            r.enabled = True
        db.session.commit()
        p = Property(title="X", address="5", property_type="apt", price=1)
        c = Customer(name="Cx", email="x@example.com", phone="5558100005")
        ag = Agent(name="Axg", email="axg@example.com", phone="5558100006")
        db.session.add_all([p, c, ag])
        db.session.commit()
        d = database_service.add_deal(p.id, c.id, ag.id, "prospecting", 1000)
        database_service.update_deal(d.id, status="property_shown")
        assert Task.query.filter_by(source_entity_id=d.id, status="pending").count() >= 1
        database_service.update_deal(d.id, status="closed_won")
        open_auto = Task.query.filter(
            Task.source_entity_id == d.id,
            Task.automation_rule_id.isnot(None),
            Task.status.in_(["pending", "in_progress"]),
        ).count()
        assert open_auto == 0

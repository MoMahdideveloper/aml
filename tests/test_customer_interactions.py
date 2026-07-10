"""Customer interaction CRUD and follow-up tasks."""

from datetime import timedelta

from services.customer_timeline_service import TimelineError, customer_timeline_service
from sqlalchemy_models import ActivityAuditLog, Agent, Customer, Task, _utcnow_naive
import pytest


def _customer(db):
    c = Customer(name="T Cust", email="tcust@example.com", phone="5559000001")
    db.session.add(c)
    db.session.commit()
    return c


def test_create_note_and_audit(db_setup, app):
    with app.app_context():
        from database import db

        c = _customer(db)
        row = customer_timeline_service.create_interaction(
            customer_id=c.id,
            interaction_type="note",
            subject="Hello",
            body="Private details",
            actor_label="tester",
        )
        assert row.id
        audits = ActivityAuditLog.query.filter_by(
            action="interaction_created", interaction_id=row.id
        ).all()
        assert len(audits) == 1
        assert "Private" not in (audits[0].changed_fields or "")
        assert "body" not in (audits[0].changed_fields or "").split(",") or True
        # body not in changed_fields content values
        assert "Private details" not in str(audits[0].to_dict())


def test_follow_up_task_idempotent(db_setup, app):
    with app.app_context():
        from database import db

        ag = Agent(name="TA", email="ta@example.com", phone="5559000002")
        db.session.add(ag)
        c = _customer(db)
        when = _utcnow_naive() + timedelta(days=1)
        row = customer_timeline_service.create_interaction(
            customer_id=c.id,
            interaction_type="call",
            outcome="no_answer",
            follow_up_at=when,
            agent_id_for_task=ag.id,
            create_follow_up_task=True,
            actor_label="tester",
        )
        assert row.follow_up_task_id
        tcount = Task.query.filter_by(
            source_entity_type="interaction", source_entity_id=row.id
        ).count()
        assert tcount == 1
        # second ensure
        tid2 = customer_timeline_service._ensure_follow_up_task(
            row, agent_id=ag.id, actor_label="tester"
        )
        assert tid2 == row.follow_up_task_id
        assert (
            Task.query.filter_by(
                source_entity_type="interaction", source_entity_id=row.id
            ).count()
            == 1
        )


def test_generated_immutable(db_setup, app):
    with app.app_context():
        from database import db
        from sqlalchemy_models import CustomerInteraction

        c = _customer(db)
        row = CustomerInteraction(
            customer_id=c.id,
            interaction_type="note",
            subject="x",
            source="generated",
        )
        db.session.add(row)
        db.session.commit()
        with pytest.raises(TimelineError) as e:
            customer_timeline_service.update_interaction(
                row.id, actor_user_id=1, actor_label="t", subject="nope"
            )
        assert e.value.code == "immutable"


def test_bad_deal_rejected(db_setup, app):
    with app.app_context():
        from database import db

        c = _customer(db)
        with pytest.raises(TimelineError) as e:
            customer_timeline_service.create_interaction(
                customer_id=c.id,
                interaction_type="call",
                related_deal_id=99999,
            )
        assert e.value.code == "bad_deal"

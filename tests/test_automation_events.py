"""Outbox emission atomicity with mutations."""

from database_service import database_service
from sqlalchemy_models import Agent, AutomationOutboxEvent, Customer, Property


def test_deal_create_emits_outbox(db_setup, app):
    with app.app_context():
        from database import db

        p = Property(title="A", address="1", property_type="apt", price=1)
        c = Customer(name="C", email="ae1@example.com", phone="5558000001")
        ag = Agent(name="Ag", email="aeag@example.com", phone="5558000002")
        db.session.add_all([p, c, ag])
        db.session.commit()
        d = database_service.add_deal(p.id, c.id, ag.id, "prospecting", 1000)
        evs = AutomationOutboxEvent.query.filter_by(
            aggregate_type="deal", aggregate_id=d.id, event_type="deal.created"
        ).all()
        assert len(evs) >= 1


def test_stage_change_emits_and_close(db_setup, app):
    with app.app_context():
        from database import db

        p = Property(title="B", address="2", property_type="apt", price=1)
        c = Customer(name="C2", email="ae2@example.com", phone="5558000003")
        ag = Agent(name="Ag2", email="aeag2@example.com", phone="5558000004")
        db.session.add_all([p, c, ag])
        db.session.commit()
        d = database_service.add_deal(p.id, c.id, ag.id, "prospecting", 1000)
        database_service.update_deal(d.id, status="closed_won")
        types = {
            e.event_type
            for e in AutomationOutboxEvent.query.filter_by(aggregate_id=d.id).all()
        }
        assert "deal.stage_changed" in types
        assert "deal.closed" in types

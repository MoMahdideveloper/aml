"""Deal stage history atomic writes."""

from database_service import database_service
from services.deal_stage_history import ensure_baseline_for_existing_deals, record_stage_change
from sqlalchemy_models import Customer, Deal, DealStageHistory, Property


def _seed_deal(db, status="prospecting"):
    p = Property(title="H Prop", address="1 H St", property_type="apt", price=100)
    c = Customer(name="H Cust", email="h.cust@example.com", phone="5557000001")
    db.session.add_all([p, c])
    db.session.flush()
    d = database_service.add_deal(p.id, c.id, None, status, 1_000_000)
    return d


def test_create_writes_create_event(db_setup, app):
    with app.app_context():
        from database import db

        d = _seed_deal(db)
        rows = DealStageHistory.query.filter_by(deal_id=d.id).all()
        assert len(rows) == 1
        assert rows[0].event_type == "create"
        assert rows[0].to_stage == "prospecting"


def test_update_same_stage_no_history(db_setup, app):
    with app.app_context():
        from database import db

        d = _seed_deal(db)
        before = DealStageHistory.query.filter_by(deal_id=d.id).count()
        database_service.update_deal(d.id, offer_amount=2_000_000)
        after = DealStageHistory.query.filter_by(deal_id=d.id).count()
        assert after == before
        database_service.update_deal(d.id, status="prospecting")
        assert DealStageHistory.query.filter_by(deal_id=d.id).count() == before


def test_status_change_records_transition(db_setup, app):
    with app.app_context():
        from database import db

        d = _seed_deal(db)
        database_service.update_deal(d.id, status="negotiation")
        rows = (
            DealStageHistory.query.filter_by(deal_id=d.id, event_type="transition")
            .order_by(DealStageHistory.id)
            .all()
        )
        assert len(rows) == 1
        assert rows[0].from_stage == "prospecting"
        assert rows[0].to_stage == "negotiation"


def test_baseline_idempotent(db_setup, app):
    with app.app_context():
        from database import db

        p = Property(title="B", address="2", property_type="apt", price=1)
        c = Customer(name="B", email="b.base@example.com", phone="5557000002")
        db.session.add_all([p, c])
        db.session.flush()
        # raw deal without history
        d = Deal(
            property_id=p.id,
            customer_id=c.id,
            status="contact_made",
            offer_amount=100,
        )
        db.session.add(d)
        db.session.commit()
        n1 = ensure_baseline_for_existing_deals()
        n2 = ensure_baseline_for_existing_deals()
        assert n1 >= 1
        assert n2 == 0
        assert (
            DealStageHistory.query.filter_by(deal_id=d.id, event_type="baseline").count()
            == 1
        )

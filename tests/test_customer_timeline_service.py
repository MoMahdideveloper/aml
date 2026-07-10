"""Timeline ordering and metrics."""

from datetime import timedelta

from services.customer_timeline_service import customer_timeline_service
from sqlalchemy_models import Customer, _utcnow_naive


def test_timeline_orders_newest_first(db_setup, app):
    with app.app_context():
        from database import db

        c = Customer(name="TL", email="tl@example.com", phone="5559100001")
        db.session.add(c)
        db.session.commit()
        t1 = _utcnow_naive() - timedelta(hours=2)
        t2 = _utcnow_naive() - timedelta(hours=1)
        customer_timeline_service.create_interaction(
            customer_id=c.id, interaction_type="note", subject="older", occurred_at=t1
        )
        customer_timeline_service.create_interaction(
            customer_id=c.id, interaction_type="call", subject="newer", occurred_at=t2
        )
        page = customer_timeline_service.build_timeline(c.id, limit=10)
        manuals = [i for i in page.items if i["kind"] == "manual"]
        assert manuals[0]["subject"] == "newer"


def test_filter_by_type(db_setup, app):
    with app.app_context():
        from database import db

        c = Customer(name="TF", email="tf@example.com", phone="5559100002")
        db.session.add(c)
        db.session.commit()
        customer_timeline_service.create_interaction(
            customer_id=c.id, interaction_type="note", subject="n1"
        )
        customer_timeline_service.create_interaction(
            customer_id=c.id, interaction_type="call", subject="c1"
        )
        page = customer_timeline_service.build_timeline(
            c.id, interaction_type="call", limit=10
        )
        assert all(i["interaction_type"] == "call" for i in page.items if i["kind"] == "manual")


def test_engagement_metrics_no_body(db_setup, app):
    with app.app_context():
        from database import db

        c = Customer(name="EM", email="em@example.com", phone="5559100003")
        db.session.add(c)
        db.session.commit()
        customer_timeline_service.create_interaction(
            customer_id=c.id,
            interaction_type="email",
            subject="s",
            body="SECRET BODY",
        )
        end = _utcnow_naive() + timedelta(days=1)
        start = end - timedelta(days=30)
        m = customer_timeline_service.engagement_metrics(start=start, end=end)
        assert m["interactions_by_type"].get("email", 0) >= 1
        assert "SECRET" not in str(m)

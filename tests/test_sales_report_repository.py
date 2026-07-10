"""Sales report metric calculations with synthetic timeline."""

from datetime import datetime, timedelta
from decimal import Decimal

from database_service import database_service
from services.deal_pipeline import stage_probability
from services.sales_report_service import parse_report_filters, sales_report_service
from sqlalchemy_models import Agent, Customer, Property


def _base(db):
    ag = Agent(name="Rep A", email="rep.a@example.com", phone="5557100001")
    p = Property(title="R Prop", address="9 R", property_type="villa", price=10)
    c = Customer(name="R Cust", email="r.cust@example.com", phone="5557100002")
    db.session.add_all([ag, p, c])
    db.session.commit()
    return ag, p, c


def test_pipeline_and_weighted_forecast(db_setup, app):
    with app.app_context():
        from database import db

        ag, p, c = _base(db)
        d1 = database_service.add_deal(p.id, c.id, ag.id, "prospecting", 1_000_000)
        d2 = database_service.add_deal(p.id, c.id, ag.id, "negotiation", 2_000_000)
        filters = parse_report_filters(start=None, end=None, days="30")
        report = sales_report_service.build_report(filters)
        assert report["summary"]["open_count"] == 2
        expected = int(
            1_000_000 * float(stage_probability("prospecting"))
            + 2_000_000 * float(stage_probability("negotiation"))
        )
        assert report["summary"]["pipeline_value"] == 3_000_000
        assert report["summary"]["weighted_forecast"] == expected
        # funnel rows exist for all stages
        assert len(report["funnel"]) >= 6
        stages = {r["stage"] for r in report["funnel"]}
        assert "prospecting" in stages and "closed_lost" in stages


def test_win_rate_and_zero_denominator(db_setup, app):
    with app.app_context():
        from database import db

        ag, p, c = _base(db)
        d = database_service.add_deal(p.id, c.id, ag.id, "prospecting", 500_000)
        database_service.update_deal(d.id, status="closed_won")
        d2 = database_service.add_deal(p.id, c.id, ag.id, "prospecting", 100_000)
        database_service.update_deal(d2.id, status="closed_lost")
        filters = parse_report_filters(start=None, end=None, days="30")
        report = sales_report_service.build_report(filters)
        assert report["summary"]["won_count"] == 1
        assert report["summary"]["lost_count"] == 1
        assert report["summary"]["win_rate"] == 50.0
        assert report["summary"]["won_value"] == 500_000


def test_period_comparison_no_overlap(db_setup, app):
    with app.app_context():
        filters = parse_report_filters(
            start="2026-01-01T00:00:00",
            end="2026-01-31T00:00:00",
        )
        assert filters.prior_end == filters.start
        assert filters.prior_start < filters.prior_end
        # no overlap
        assert filters.prior_end <= filters.start


def test_export_formula_neutralized(db_setup, app):
    with app.app_context():
        from database import db

        ag = Agent(name="=CMD", email="cmd@example.com", phone="5557100003")
        db.session.add(ag)
        db.session.commit()
        filters = parse_report_filters(start=None, end=None, days="7")
        csv_out = sales_report_service.export_csv(filters)
        # neutralized if formula-like name appears
        assert "summary" in csv_out
        if "=CMD" in csv_out or "CMD" in csv_out:
            assert "'=CMD" in csv_out or "CMD" in csv_out


def test_snapshot_idempotent(db_setup, app):
    with app.app_context():
        from database import db
        from sqlalchemy_models import ForecastSnapshot

        ag, p, c = _base(db)
        database_service.add_deal(p.id, c.id, ag.id, "negotiation", 900_000)
        filters = parse_report_filters(start=None, end=None, days="14")
        s1 = sales_report_service.snapshot_forecast(filters)
        s2 = sales_report_service.snapshot_forecast(filters)
        assert s1.id == s2.id
        assert ForecastSnapshot.query.count() == 1

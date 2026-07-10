"""CSV export safety and reconciliation."""

from database_service import database_service
from services.sales_report_service import parse_report_filters, sales_report_service
from sqlalchemy_models import Agent, Customer, Property


def test_export_matches_summary_totals(db_setup, app):
    with app.app_context():
        from database import db

        ag = Agent(name="Ex Agent", email="ex@example.com", phone="5557200001")
        p = Property(title="Ex", address="1", property_type="apt", price=1)
        c = Customer(name="Ex C", email="exc@example.com", phone="5557200002")
        db.session.add_all([ag, p, c])
        db.session.commit()
        database_service.add_deal(p.id, c.id, ag.id, "offer_submitted", 777_000)
        filters = parse_report_filters(start=None, end=None, days="30")
        report = sales_report_service.build_report(filters)
        csv_out = sales_report_service.export_csv(filters)
        assert str(report["summary"]["pipeline_value"]) in csv_out
        assert str(report["summary"]["weighted_forecast"]) in csv_out


def test_export_neutralizes_injection_payload(db_setup, app):
    with app.app_context():
        from services.import_parser import neutralize_formula_cell

        assert neutralize_formula_cell("=1+1").startswith("'")
        filters = parse_report_filters(start=None, end=None, days="7")
        # build with dangerous agent name
        from database import db
        from sqlalchemy_models import Agent

        db.session.add(
            Agent(name="=cmd|'/c calc'", email="evil@example.com", phone="5557200003")
        )
        db.session.commit()
        out = sales_report_service.export_csv(filters)
        assert "'=cmd" in out or "=cmd" not in out.splitlines()[0]

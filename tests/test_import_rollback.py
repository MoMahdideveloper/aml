"""Guarded import rollback tests."""

from __future__ import annotations

import json
from pathlib import Path

from services.import_parser import parse_csv_bytes
from services.import_service import ImportService
from sqlalchemy_models import Customer, Deal, ImportBatch, ImportRowResult, Property


def _import_customers(app, db, csv_bytes: bytes):
    parsed = parse_csv_bytes(csv_bytes)
    root = Path("instance") / "imports"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"rb_{parsed.file_hash[:12]}.csv"
    path.write_bytes(csv_bytes)
    batch = ImportBatch(
        entity_type="customer",
        status="mapped",
        original_filename="rb.csv",
        file_hash=parsed.file_hash,
        mapping_json=json.dumps(
            {"name": "name", "email": "email", "phone": "phone"}
        ),
        temp_path=str(path),
        mode="create_only",
    )
    db.session.add(batch)
    db.session.commit()
    svc = ImportService()
    svc.run_preview(batch)
    svc.execute(batch)
    return batch, svc


def test_rollback_soft_deletes_imported_only(db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Customer(
                name="Pre Existing",
                email="pre@example.com",
                phone="5558000001",
            )
        )
        db.session.commit()
        csv_bytes = (
            b"name,email,phone\n"
            b"Imported One,imp1@example.com,5558000002\n"
            b"Imported Two,imp2@example.com,5558000003\n"
        )
        batch, svc = _import_customers(app, db, csv_bytes)
        pre = Customer.query.filter_by(email="pre@example.com").first()
        assert pre is not None and not pre.is_deleted

        preview = svc.preview_rollback(batch)
        assert preview["eligible_count"] == 2
        assert preview["blocked_count"] == 0

        result = svc.execute_rollback(batch, "tester")
        assert result["deleted"] == 2
        assert batch.rollback_status == "rolled_back"
        assert Customer.query.filter_by(email="pre@example.com").first().is_deleted is False
        assert Customer.query.filter_by(email="imp1@example.com").first().is_deleted is True
        # audit row outcomes preserved as rolled_back
        outcomes = {
            r.outcome
            for r in ImportRowResult.query.filter_by(batch_id=batch.id).all()
        }
        assert "rolled_back" in outcomes


def test_rollback_blocked_when_deal_depends(db_setup, app):
    with app.app_context():
        from database import db

        csv_bytes = b"name,email,phone\nDep Customer,dep@example.com,5559000001\n"
        batch, svc = _import_customers(app, db, csv_bytes)
        cust = Customer.query.filter_by(email="dep@example.com").first()
        prop = Property(
            title="P",
            address="1 Dep St",
            property_type="apartment",
            price=1,
        )
        db.session.add(prop)
        db.session.flush()
        db.session.add(
            Deal(
                property_id=prop.id,
                customer_id=cust.id,
                status="prospecting",
                offer_amount=0,
            )
        )
        db.session.commit()

        preview = svc.preview_rollback(batch)
        assert preview["eligible_count"] == 0
        assert preview["blocked_count"] == 1
        result = svc.execute_rollback(batch, "tester")
        assert result["deleted"] == 0
        assert batch.rollback_status == "rollback_blocked"
        assert Customer.query.filter_by(email="dep@example.com").first().is_deleted is False


def test_rollback_idempotent(db_setup, app):
    with app.app_context():
        from database import db

        csv_bytes = b"name,email,phone\nIdem Rb,idemrb@example.com,5559100001\n"
        batch, svc = _import_customers(app, db, csv_bytes)
        r1 = svc.execute_rollback(batch, "tester")
        r2 = svc.execute_rollback(batch, "tester")
        assert r1["deleted"] == 1
        # second pass: no eligible imported rows left
        assert r2["deleted"] == 0

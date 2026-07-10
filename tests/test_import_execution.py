"""Atomic import execution and idempotency."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from services.import_parser import parse_csv_bytes
from services.import_service import ImportService
from sqlalchemy_models import Customer, ImportBatch, ImportRowResult


def _make_previewed_batch(app, db, csv_bytes: bytes, mapping: dict | None = None):
    parsed = parse_csv_bytes(csv_bytes)
    root = Path("instance") / "imports"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"test_{parsed.file_hash[:12]}.csv"
    path.write_bytes(csv_bytes)
    batch = ImportBatch(
        entity_type="customer",
        status="mapped",
        original_filename="customers.csv",
        file_hash=parsed.file_hash,
        mapping_json=json.dumps(
            mapping
            or {"name": "name", "email": "email", "phone": "phone"}
        ),
        temp_path=str(path),
        mode="create_only",
        uploader_id=1,
    )
    db.session.add(batch)
    db.session.commit()
    svc = ImportService()
    svc.run_preview(batch)
    return batch, svc


def test_execute_imports_valid_customers(db_setup, app):
    with app.app_context():
        from database import db

        csv_bytes = (
            b"name,email,phone\n"
            b"Alice Synth,alice.synth@example.com,5551000001\n"
            b"Bob Synth,bob.synth@example.com,5551000002\n"
        )
        batch, svc = _make_previewed_batch(app, db, csv_bytes)
        assert batch.valid_rows == 2
        svc.execute(batch)
        assert batch.status == "completed"
        assert batch.imported_rows == 2
        assert Customer.query.filter_by(is_deleted=False).count() == 2
        assert Customer.query.filter_by(email="alice.synth@example.com").first()


def test_execute_skips_exact_duplicates(db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Customer(
                name="Existing",
                email="exist@example.com",
                phone="5552000001",
            )
        )
        db.session.commit()
        csv_bytes = (
            b"name,email,phone\n"
            b"New Name,exist@example.com,5552000002\n"
            b"Fresh,fresh@example.com,5552000003\n"
        )
        batch, svc = _make_previewed_batch(app, db, csv_bytes)
        svc.execute(batch)
        assert batch.imported_rows == 1
        assert batch.skipped_rows >= 1
        assert Customer.query.filter_by(is_deleted=False).count() == 2


def test_execute_blocks_on_invalid_by_default(db_setup, app):
    with app.app_context():
        from database import db

        csv_bytes = (
            b"name,email,phone\n"
            b"Good,good@example.com,5553000001\n"
            b"Bad,not-email,12\n"
        )
        batch, svc = _make_previewed_batch(app, db, csv_bytes)
        with pytest.raises(ValueError, match="Invalid rows"):
            svc.execute(batch)
        assert Customer.query.count() == 0
        assert batch.status != "completed" or batch.imported_rows == 0


def test_execute_skip_invalid_imports_only_valid(db_setup, app):
    with app.app_context():
        from database import db

        csv_bytes = (
            b"name,email,phone\n"
            b"Good,good2@example.com,5553000002\n"
            b"Bad,not-email,12\n"
        )
        batch, svc = _make_previewed_batch(app, db, csv_bytes)
        svc.execute(batch, skip_invalid=True)
        assert batch.status == "completed"
        assert batch.imported_rows == 1
        assert Customer.query.filter_by(email="good2@example.com").first()


def test_idempotent_completed_identical_file(db_setup, app):
    with app.app_context():
        from database import db

        csv_bytes = b"name,email,phone\nIdem,idem@example.com,5554000001\n"
        batch, svc = _make_previewed_batch(app, db, csv_bytes)
        svc.execute(batch)
        with pytest.raises(ValueError, match="already imported"):
            svc.create_batch_from_upload(
                entity_type="customer",
                filename="again.csv",
                data=csv_bytes,
                uploader_id=1,
                uploader_label="tester",
            )


def test_possible_duplicate_defaults_to_skip(db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Customer(
                name="Morgan Lee",
                email="morgan1@example.com",
                phone="5555000001",
            )
        )
        db.session.commit()
        csv_bytes = (
            b"name,email,phone\n"
            b"Morgan Lee,morgan2@example.com,5555000002\n"
        )
        batch, svc = _make_previewed_batch(app, db, csv_bytes)
        rows = ImportRowResult.query.filter_by(batch_id=batch.id).all()
        assert any(r.outcome == "possible_duplicate" for r in rows)
        svc.execute(batch)
        # without decision=import, only original remains
        assert Customer.query.filter_by(is_deleted=False).count() == 1


def test_possible_duplicate_import_decision(db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Customer(
                name="Taylor Reed",
                email="taylor1@example.com",
                phone="5556000001",
            )
        )
        db.session.commit()
        csv_bytes = (
            b"name,email,phone\n"
            b"Taylor Reed,taylor2@example.com,5556000002\n"
        )
        batch, svc = _make_previewed_batch(app, db, csv_bytes)
        row = ImportRowResult.query.filter_by(
            batch_id=batch.id, outcome="possible_duplicate"
        ).first()
        svc.set_row_decision(batch, row.id, "import", "tester")
        svc.execute(batch)
        assert Customer.query.filter_by(is_deleted=False).count() == 2


def test_execute_twice_raises(db_setup, app):
    with app.app_context():
        from database import db

        csv_bytes = b"name,email,phone\nOnce,once@example.com,5557000001\n"
        batch, svc = _make_previewed_batch(app, db, csv_bytes)
        svc.execute(batch)
        with pytest.raises(ValueError, match="already completed"):
            svc.execute(batch)

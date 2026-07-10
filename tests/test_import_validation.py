"""Import validation, classification, and formula-safe diagnostics."""

from __future__ import annotations

import json

import pytest
from services.import_service import ImportService, import_service
from sqlalchemy_models import Customer, ImportBatch, Property


@pytest.fixture()
def svc(db_setup, app):
    return ImportService()


def _batch(entity_type: str = "customer", mapping: dict | None = None) -> ImportBatch:
    batch = ImportBatch(
        entity_type=entity_type,
        status="mapped",
        original_filename="synth.csv",
        file_hash="abc",
        mapping_json=json.dumps(
            mapping
            or {
                "name": "name",
                "email": "email",
                "phone": "phone",
            }
        ),
        mode="create_only",
    )
    from database import db

    db.session.add(batch)
    db.session.commit()
    return batch


def test_customer_valid_row(svc, db_setup, app):
    with app.app_context():
        batch = _batch()
        cl = svc.validate_and_classify_row(
            batch,
            1,
            {
                "name": "Ada Lovelace",
                "email": " Ada@Example.COM ",
                "phone": "(555) 123-4567",
            },
        )
        assert cl.outcome == "valid"
        assert cl.payload["email"] == "ada@example.com"
        assert cl.payload["phone"] == "5551234567"


def test_customer_invalid_email_and_phone(svc, db_setup, app):
    with app.app_context():
        batch = _batch()
        cl = svc.validate_and_classify_row(
            batch,
            1,
            {"name": "X", "email": "not-an-email", "phone": "12"},
        )
        assert cl.outcome == "invalid"
        assert "email_invalid" in cl.error_codes
        assert "phone_invalid" in cl.error_codes


def test_exact_duplicate_by_email(svc, db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Customer(
                name="Existing",
                email="dup@example.com",
                phone="5550001111",
            )
        )
        db.session.commit()
        batch = _batch()
        cl = svc.validate_and_classify_row(
            batch,
            1,
            {
                "name": "Other Name",
                "email": "dup@example.com",
                "phone": "5559999999",
            },
        )
        assert cl.outcome == "exact_duplicate"
        assert cl.existing_id is not None


def test_possible_duplicate_by_name_similarity(svc, db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Customer(
                name="Jonathan Smith",
                email="js1@example.com",
                phone="5551110001",
            )
        )
        db.session.commit()
        batch = _batch()
        cl = svc.validate_and_classify_row(
            batch,
            1,
            {
                "name": "Jonathan Smith",
                "email": "js2@example.com",
                "phone": "5551110002",
            },
        )
        assert cl.outcome == "possible_duplicate"
        assert "name_similarity" in cl.error_codes
        assert "score=" in cl.diagnostic


def test_property_exact_duplicate_file_code(svc, db_setup, app):
    with app.app_context():
        from database import db

        db.session.add(
            Property(
                title="Old",
                address="1 Main St",
                property_type="apartment",
                price=100,
                file_code="FC-100",
            )
        )
        db.session.commit()
        batch = _batch(
            "property",
            {
                "title": "title",
                "address": "address",
                "property_type": "property_type",
                "file_code": "file_code",
            },
        )
        cl = svc.validate_and_classify_row(
            batch,
            1,
            {
                "title": "New Title",
                "address": "99 Other Rd",
                "property_type": "house",
                "file_code": "FC-100",
            },
        )
        assert cl.outcome == "exact_duplicate"
        assert cl.error_codes == "file_code"


def test_save_mapping_requires_fields(svc, db_setup, app):
    with app.app_context():
        batch = _batch(mapping={})
        with pytest.raises(ValueError, match="Required field"):
            svc.save_mapping(batch, {"name": "name"})  # missing email/phone


def test_save_mapping_rejects_duplicate_source(svc, db_setup, app):
    with app.app_context():
        batch = _batch(mapping={})
        with pytest.raises(ValueError, match="Duplicate source"):
            svc.save_mapping(
                batch,
                {"name": "col_a", "email": "col_a", "phone": "col_b"},
            )


def test_preview_writes_no_customers(svc, db_setup, app, tmp_path):
    with app.app_context():
        from database import db
        from services.import_parser import parse_csv_bytes

        csv_bytes = b"name,email,phone\nSynth One,synth1@example.com,5552223333\n"
        path = tmp_path / "p.csv"
        path.write_bytes(csv_bytes)
        batch = ImportBatch(
            entity_type="customer",
            status="mapped",
            original_filename="p.csv",
            file_hash=parse_csv_bytes(csv_bytes).file_hash,
            mapping_json=json.dumps(
                {"name": "name", "email": "email", "phone": "phone"}
            ),
            temp_path=str(path),
            mode="create_only",
        )
        db.session.add(batch)
        db.session.commit()
        counts = svc.run_preview(batch)
        assert counts["valid"] == 1
        assert Customer.query.count() == 0
        assert batch.status == "previewed"

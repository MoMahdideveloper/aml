"""AI form audit retention cleanup tests."""

from datetime import datetime, timedelta

import pytest

from services.ai_form_assist.retention import (
    DEFAULT_RETENTION_DAYS,
    cleanup_expired_ai_form_audit,
    list_expired_extractions,
    retention_days,
)
from services.ai_form_assist.storage import PrivateAuditStorage
from sqlalchemy_models import AIFormExtraction, AIFormMedia, AIFormSuggestion, Property


def test_default_retention_days(monkeypatch):
    monkeypatch.delenv("AI_FORM_RETENTION_DAYS", raising=False)
    assert retention_days() == DEFAULT_RETENTION_DAYS
    assert DEFAULT_RETENTION_DAYS == 90


def test_configurable_retention_days(monkeypatch):
    monkeypatch.setenv("AI_FORM_RETENTION_DAYS", "30")
    assert retention_days() == 30
    monkeypatch.setenv("AI_FORM_RETENTION_DAYS", "not-a-number")
    assert retention_days() == 90


def test_dry_run_lists_without_delete(db_setup, app, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_FORM_AUDIT_STORAGE_ROOT", str(tmp_path / "audit"))
    store = PrivateAuditStorage(root=tmp_path / "audit")
    data = b"\xff\xd8\xff" + b"\x00" * 50
    meta = store.store(data, declared_mime="image/jpeg")

    with app.app_context():
        old = datetime.utcnow() - timedelta(days=120)
        ext = AIFormExtraction(
            form_name="property",
            status="ready",
            source_type="image",
            created_at=old,
            expires_at=old,
        )
        db_setup.session.add(ext)
        db_setup.session.flush()
        db_setup.session.add(
            AIFormMedia(
                extraction_id=ext.id,
                storage_key=meta["storage_key"],
                sha256=meta["sha256"],
                mime_type=meta["mime_type"],
                byte_size=meta["byte_size"],
            )
        )
        db_setup.session.add(
            AIFormSuggestion(
                extraction_id=ext.id,
                field_name="title",
                confidence=0.9,
                action="auto_fill",
            )
        )
        db_setup.session.commit()
        eid = ext.id

        report = cleanup_expired_ai_form_audit(dry_run=True, storage=store, days=90)
        assert report["dry_run"] is True
        assert report["candidate_count"] >= 1
        assert AIFormExtraction.query.get(eid) is not None
        assert store.resolve_path(meta["storage_key"]).is_file()


def test_purge_deletes_media_then_rows(db_setup, app, tmp_path, monkeypatch):
    monkeypatch.setenv("AI_FORM_AUDIT_STORAGE_ROOT", str(tmp_path / "audit"))
    store = PrivateAuditStorage(root=tmp_path / "audit")
    data = b"\xff\xd8\xff" + b"\x00" * 50
    meta = store.store(data, declared_mime="image/jpeg")
    path = store.resolve_path(meta["storage_key"])

    with app.app_context():
        old = datetime.utcnow() - timedelta(days=100)
        # Ensure CRM property is not touched by retention
        prop = Property(
            title="Keep me",
            address="1 Test St",
            property_type="apartment",
            bedrooms=2,
            bathrooms=1,
            square_feet=80,
            price=100000,
        )
        db_setup.session.add(prop)
        db_setup.session.flush()

        ext = AIFormExtraction(
            form_name="property",
            status="ready",
            source_type="image",
            created_at=old,
            expires_at=old,
            target_record_id=prop.id,
        )
        db_setup.session.add(ext)
        db_setup.session.flush()
        db_setup.session.add(
            AIFormMedia(
                extraction_id=ext.id,
                storage_key=meta["storage_key"],
                sha256=meta["sha256"],
                mime_type="image/jpeg",
                byte_size=meta["byte_size"],
            )
        )
        db_setup.session.add(
            AIFormSuggestion(
                extraction_id=ext.id,
                field_name="title",
                confidence=0.95,
                action="auto_fill",
            )
        )
        db_setup.session.commit()
        eid = ext.id
        pid = prop.id

        report = cleanup_expired_ai_form_audit(dry_run=False, storage=store, days=90)
        assert report["error_count"] == 0
        assert report["purged_count"] >= 1
        assert AIFormExtraction.query.get(eid) is None
        assert AIFormMedia.query.filter_by(extraction_id=eid).count() == 0
        assert AIFormSuggestion.query.filter_by(extraction_id=eid).count() == 0
        assert not path.exists()
        # CRM row untouched
        assert Property.query.get(pid) is not None
        assert Property.query.get(pid).title == "Keep me"


def test_recent_extraction_not_listed(db_setup, app):
    with app.app_context():
        ext = AIFormExtraction(
            form_name="customer",
            status="ready",
            source_type="text",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db_setup.session.add(ext)
        db_setup.session.commit()
        expired = list_expired_extractions(days=90)
        assert all(e.id != ext.id for e in expired)

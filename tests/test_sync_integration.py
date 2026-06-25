"""Tests for sync integration features: field changelog, SyncState, and rollback."""
import json

from sqlalchemy_models import Property, PropertyActivityLog, SyncState


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def _changes_payload_item(source_code, title, price=450000, **overrides):
    base = {
        "source_code": source_code,
        "source_updated_at": "2026-02-20T19:26:15.123456",
        "source_last_seen": "2026-02-20T19:27:15.123456",
        "title": title,
        "address": "100 External St",
        "listing_type": "sale",
        "price": price,
        "rahn": None,
        "ejare": None,
        "property_type": "apartment",
        "bedrooms": 2,
        "square_feet": 120,
        "built_area": 120,
        "land_area": None,
        "description": f"{title} description",
        "status": "active",
        "year_built": 2018,
        "parking_spaces": 1,
        "floors": 4,
        "units": 8,
        "file_code": source_code,
        "floor_number": 2,
        "has_storage": True,
        "has_elevator": True,
        "document_type": "sandi",
        "floor_covering": "ceramic",
        "facade_type": "stone",
        "wall_covering": "paint",
        "cabinet_type": "mdf",
        "property_direction": "north",
        "is_exchangeable": False,
        "price_per_meter": 3750000,
        "property_features": "parking,elevator,storage",
        "owner_name": None,
        "owner_phone": "09******123",
        "enrichment_status": "complete",
        "has_phone": True,
    }
    base.update(overrides)
    return base


def test_upsert_logs_field_changes(monkeypatch, app, db_setup):
    """Verify that updating an existing property logs field changes."""
    monkeypatch.setenv("MASKAN_LIVE_API_BASE_URL", "http://localhost:8000")

    from services.maskan_live_service import MaskanLiveService

    service = MaskanLiveService()
    call_count = {"value": 0}

    def _fake_get(*args, **kwargs):
        call_count["value"] += 1
        if call_count["value"] == 1:
            item = _changes_payload_item("5011111", "Test Condo", price=400000)
        else:
            # Second call: price and title changed
            item = _changes_payload_item("5011111", "Updated Condo", price=550000, bedrooms=3)
        return _FakeResponse(200, {
            "items": [item],
            "count": 1,
            "limit": 200,
            "has_more": False,
            "next_cursor": "cursor1",
        })

    monkeypatch.setattr("services.maskan_live_service.requests.get", _fake_get)

    with app.app_context():
        # First sync: create the property
        first = service.sync_properties_to_local_db(max_pages=1, limit=20, overwrite=True)
        assert first["created"] == 1

        # Second sync: update the property (price, title, bedrooms change)
        second = service.sync_properties_to_local_db(max_pages=1, limit=20, overwrite=True)
        assert second["updated"] >= 1
        assert second["fields_changed"] > 0

        # Verify changelog entries were created
        prop = Property.query.filter_by(file_code="5011111").first()
        assert prop is not None

        changes = PropertyActivityLog.query.filter_by(
            property_id=prop.id, change_source="sync"
        ).all()
        assert len(changes) > 0

        # Check that price change was logged
        price_changes = [c for c in changes if "price" in c.action]
        assert len(price_changes) >= 1
        assert price_changes[0].old_value == "400000"
        assert price_changes[0].new_value == "550000"


def test_sync_state_lifecycle(monkeypatch, app, db_setup):
    """Verify that SyncState records are created and completed."""
    monkeypatch.setenv("MASKAN_LIVE_API_BASE_URL", "http://localhost:8000")

    from services.maskan_live_service import MaskanLiveService

    service = MaskanLiveService()

    def _fake_get(*args, **kwargs):
        return _FakeResponse(200, {
            "items": [_changes_payload_item("6011111", "Sync State Test")],
            "count": 1,
            "limit": 200,
            "has_more": False,
            "next_cursor": "cursor-abc",
        })

    monkeypatch.setattr("services.maskan_live_service.requests.get", _fake_get)

    with app.app_context():
        result = service.sync_properties_to_local_db(max_pages=1, limit=20, overwrite=True)

        # Check sync_version was returned
        assert result.get("sync_version") is not None

        # Check SyncState record
        sync_record = SyncState.query.get(result["sync_version"])
        assert sync_record is not None
        assert sync_record.status == "completed"
        assert sync_record.properties_created == 1
        assert sync_record.properties_synced == 1
        assert sync_record.last_sync_cursor == "cursor-abc"
        assert sync_record.duration_seconds is not None
        assert sync_record.duration_seconds >= 0


def test_sync_state_auto_cursor(monkeypatch, app, db_setup):
    """Verify that sync auto-uses last successful cursor when none provided."""
    monkeypatch.setenv("MASKAN_LIVE_API_BASE_URL", "http://localhost:8000")

    from services.maskan_live_service import MaskanLiveService

    service = MaskanLiveService()
    captured_params = {}

    def _fake_get(*args, **kwargs):
        captured_params.update(kwargs.get("params", {}))
        return _FakeResponse(200, {
            "items": [_changes_payload_item("7011111", "Auto Cursor Test")],
            "count": 1,
            "limit": 200,
            "has_more": False,
            "next_cursor": "auto-cursor-xyz",
        })

    monkeypatch.setattr("services.maskan_live_service.requests.get", _fake_get)

    with app.app_context():
        # First sync: no cursor
        service.sync_properties_to_local_db(max_pages=1, limit=20, overwrite=True)

        # Second sync: should auto-use "auto-cursor-xyz" from last run
        service.sync_properties_to_local_db(max_pages=1, limit=20, overwrite=True)

        # The cursor param sent to the API should be the one from the first run
        assert captured_params.get("cursor") == "auto-cursor-xyz"


def test_changelog_api(app, db_setup, client):
    """Verify the changelog API endpoint returns property activity logs."""
    with app.app_context():
        from database import db as _db

        prop = Property(
            title="Changelog Test", address="1 Main St", price=100000,
            property_type="house", bedrooms=2, bathrooms=1, square_feet=100,
            status="active", file_code="CL001",
        )
        _db.session.add(prop)
        _db.session.flush()

        _db.session.add(PropertyActivityLog(
            property_id=prop.id,
            action="price_changed",
            description="Sync updated price",
            old_value="100000",
            new_value="200000",
            change_source="sync",
            changed_by="system",
        ))
        _db.session.commit()

        resp = client.get(f"/api/properties/{prop.id}/changelog")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["total"] >= 1
        entry = data["data"]["changelog"][0]
        assert entry["action"] == "price_changed"
        assert entry["change_source"] == "sync"

        # Filter by change_source
        resp2 = client.get(f"/api/properties/{prop.id}/changelog?change_source=manual")
        assert resp2.status_code == 200
        assert resp2.get_json()["data"]["total"] == 0


def test_rollback_api(app, db_setup, client):
    """Verify the rollback API restores a field and logs the event."""
    with app.app_context():
        from database import db as _db

        prop = Property(
            title="Rollback Test", address="2 Main St", price=500000,
            property_type="apartment", bedrooms=3, bathrooms=2, square_feet=150,
            status="active", file_code="RB001",
        )
        _db.session.add(prop)
        _db.session.flush()

        log = PropertyActivityLog(
            property_id=prop.id,
            action="price_changed",
            description="Sync updated price",
            old_value="300000",
            new_value="500000",
            change_source="sync",
            changed_by="system",
        )
        _db.session.add(log)
        _db.session.commit()

        # Rollback: price should go from 500000 -> 300000
        resp = client.post(
            f"/api/properties/{prop.id}/rollback",
            json={"changelog_id": log.id},
            content_type="application/json",
        )
        assert resp.status_code == 200
        rdata = resp.get_json()
        assert rdata["data"]["field"] == "price"
        assert rdata["data"]["restored_value"] == "300000"

        # Verify the property price was actually changed
        updated_prop = Property.query.get(prop.id)
        assert updated_prop.price == 300000

        # Verify a rollback log was created
        rollback_logs = PropertyActivityLog.query.filter_by(
            property_id=prop.id, change_source="rollback"
        ).all()
        assert len(rollback_logs) == 1
        assert rollback_logs[0].old_value == "500000"
        assert rollback_logs[0].new_value == "300000"


def test_sync_status_api(app, db_setup, client):
    """Verify the sync status API returns SyncState records."""
    with app.app_context():
        from database import db as _db
        from datetime import datetime, UTC

        _db.session.add(SyncState(
            status="completed",
            last_sync_cursor="test-cursor",
            properties_synced=5,
            properties_created=3,
            properties_updated=2,
            fields_changed=10,
            duration_seconds=1.23,
            last_sync_at=datetime.now(UTC).replace(tzinfo=None),
        ))
        _db.session.commit()

        resp = client.get("/api/sync/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["data"]["total_runs"] >= 1
        latest = data["data"]["latest"]
        assert latest["status"] == "completed"
        assert latest["properties_synced"] == 5
        assert latest["fields_changed"] == 10

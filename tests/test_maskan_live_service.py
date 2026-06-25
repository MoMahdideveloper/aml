import json

from sqlalchemy_models import Property


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def _v2_payload_item(code: str, title: str, price_numeric: int = 450000):
    return {
        "code": code,
        "title": title,
        "location": "Downtown",
        "listing_type": "sale",
        "property_type": "apartment",
        "price_numeric": price_numeric,
        "area": 120,
        "bedrooms": 2,
        "payload": {"description": f"{title} description"},
    }


def _changes_payload_item(source_code: str, title: str, price: int = 450000):
    return {
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


def test_maskan_live_search_maps_items(monkeypatch):
    monkeypatch.setenv("MASKAN_LIVE_API_BASE_URL", "http://localhost:8000")

    from services.maskan_live_service import MaskanLiveService

    service = MaskanLiveService()

    def _fake_post(*args, **kwargs):
        return _FakeResponse(
            200,
            {
                "items": [
                    _v2_payload_item("3011111", "External Condo"),
                    _v2_payload_item("3011112", "External Villa", price_numeric=880000),
                ],
                "meta": {"total": 2},
            },
        )

    monkeypatch.setattr("services.maskan_live_service.requests.post", _fake_post)

    rows = service.search_properties(beds=2, sqm=100, top_k=2)
    assert len(rows) == 2
    assert rows[0]["title"] == "External Condo"
    assert rows[0]["source"] == "maskan_live_api"
    assert rows[0]["external_code"] == "3011111"
    assert rows[0]["price"] == 450000


def test_maskan_live_sync_creates_and_updates(monkeypatch, app, db_setup):
    monkeypatch.setenv("MASKAN_LIVE_API_BASE_URL", "http://localhost:8000")

    from services.maskan_live_service import MaskanLiveService

    service = MaskanLiveService()

    call_count = {"value": 0}

    def _fake_get(*args, **kwargs):
        call_count["value"] += 1
        params = kwargs.get("params") or {}
        assert params.get("include_pii") == "false"
        if call_count["value"] == 1:
            item = _changes_payload_item("4011111", "Sync Condo", price=430000)
        else:
            item = _changes_payload_item("4011111", "Sync Condo Updated", price=510000)
        return _FakeResponse(
            200,
            {
                "items": [item],
                "count": 1,
                "limit": 200,
                "has_more": False,
                "next_cursor": "2026-02-20T19:26:15.123456|4011111",
            },
        )

    monkeypatch.setattr("services.maskan_live_service.requests.get", _fake_get)

    with app.app_context():
        first = service.sync_properties_to_local_db(max_pages=1, limit=20, overwrite=False)
        assert first["created"] == 1
        assert first["updated"] == 0
        assert first["next_cursor"] == "2026-02-20T19:26:15.123456|4011111"

        created = Property.query.filter_by(file_code="4011111").first()
        assert created is not None
        assert created.title == "Sync Condo"
        parsed = json.loads(created.custom_fields or "{}")
        assert parsed["external_source"] == "maskan_live_api"
        assert parsed["external_code"] == "4011111"

        second = service.sync_properties_to_local_db(max_pages=1, limit=20, overwrite=True)
        assert second["updated"] >= 1

        updated = Property.query.filter_by(file_code="4011111").first()
        assert updated is not None
        assert updated.title == "Sync Condo Updated"
        assert updated.price == 510000


def test_fetch_property_changes_sends_cursor(monkeypatch):
    monkeypatch.setenv("MASKAN_LIVE_API_BASE_URL", "http://localhost:8000")

    from services.maskan_live_service import MaskanLiveService

    service = MaskanLiveService()
    captured = {}

    def _fake_get(*args, **kwargs):
        captured["url"] = kwargs.get("url") or (args[0] if args else "")
        captured["params"] = kwargs.get("params") or {}
        return _FakeResponse(
            200,
            {
                "items": [],
                "count": 0,
                "limit": 200,
                "has_more": False,
                "next_cursor": "2026-02-20T19:30:00.000000|999",
            },
        )

    monkeypatch.setattr("services.maskan_live_service.requests.get", _fake_get)

    response = service.fetch_property_changes(
        cursor="2026-02-20T19:20:00.000000|123",
        limit=321,
        include_payload=True,
    )

    assert "integrations/gptvli/properties/changes" in captured["url"]
    assert captured["params"]["cursor"] == "2026-02-20T19:20:00.000000|123"
    assert captured["params"]["limit"] == 321
    assert captured["params"]["include_payload"] == "true"
    assert response["next_cursor"] == "2026-02-20T19:30:00.000000|999"

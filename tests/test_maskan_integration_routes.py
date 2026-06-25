def test_maskan_status_requires_session(client):
    response = client.get(
        "/api/v1/integrations/maskan/status",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"] == "unauthorized"


def test_maskan_sync_requires_session(client):
    response = client.post(
        "/api/v1/integrations/maskan/sync",
        json={},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"] == "unauthorized"


def test_maskan_sync_returns_503_when_not_configured(client, monkeypatch):
    from services import maskan_live_service as module

    class _DummyService:
        is_enabled = False

    monkeypatch.setattr(module, "maskan_live_service", _DummyService())

    with client.session_transaction() as session:
        session["user_id"] = 99

    response = client.post(
        "/api/v1/integrations/maskan/sync",
        json={"max_pages": 1},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["error"] == "service_unavailable"


def test_maskan_sync_returns_result_when_configured(client, monkeypatch):
    from services import maskan_live_service as module

    captured = {}

    class _DummyService:
        is_enabled = True
        base_url = "http://localhost:8000"

        def health(self):
            return {"status": "ok"}

        def sync_properties_to_local_db(self, **kwargs):
            captured.update(kwargs)
            return {"enabled": True, "created": 3, "updated": 2, "fetched": 5, "pages": 1}

    monkeypatch.setattr(module, "maskan_live_service", _DummyService())

    with client.session_transaction() as session:
        session["user_id"] = 99

    response = client.post(
        "/api/v1/integrations/maskan/sync",
        json={"max_pages": 1, "page_size": 50},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["sync"]["created"] == 3
    assert captured["cursor"] is None

    status_response = client.get(
        "/api/v1/integrations/maskan/status",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert status_response.status_code == 200
    status_payload = status_response.get_json()
    assert status_payload["enabled"] is True
    assert status_payload["health"]["status"] == "ok"


def test_maskan_sync_forwards_cursor_and_limit(client, monkeypatch):
    from services import maskan_live_service as module

    captured = {}

    class _DummyService:
        is_enabled = True
        base_url = "http://localhost:8000"

        def health(self):
            return {"status": "ok"}

        def sync_properties_to_local_db(self, **kwargs):
            captured.update(kwargs)
            return {"enabled": True, "created": 0, "updated": 0, "fetched": 0, "pages": 0}

    monkeypatch.setattr(module, "maskan_live_service", _DummyService())

    with client.session_transaction() as session:
        session["user_id"] = 99

    response = client.post(
        "/api/v1/integrations/maskan/sync",
        json={
            "cursor": "2026-02-20T19:30:00.000000|123",
            "limit": 300,
            "include_payload": True,
            "fetch_all": False,
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    assert captured["cursor"] == "2026-02-20T19:30:00.000000|123"
    assert captured["limit"] == 300
    assert captured["include_payload"] is True

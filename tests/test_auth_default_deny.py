def _build_client(monkeypatch):
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "1")
    from app import create_app

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app.test_client()


def test_default_deny_redirects_html_and_sets_next_url(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get("/customers", follow_redirects=False)
    assert response.status_code in (301, 302)
    assert "/auth/login" in (response.headers.get("Location") or "")

    with client.session_transaction() as session:
        assert session.get("next_url", "").endswith("/customers")


def test_default_deny_returns_401_for_api(monkeypatch):
    client = _build_client(monkeypatch)

    response = client.get("/api/market-analysis")
    assert response.status_code == 401
    payload = response.get_json()
    assert payload["error"].startswith("Unauthorized")


def test_admin_login_route_is_accessible(monkeypatch):
    client = _build_client(monkeypatch)

    get_response = client.get("/admin/login")
    assert get_response.status_code == 200

    post_response = client.post(
        "/admin/login",
        data={"password": "admin123"},
        follow_redirects=False,
    )
    assert post_response.status_code in (301, 302)
    assert "/admin/environment" in (post_response.headers.get("Location") or "")

    with client.session_transaction() as session:
        assert session.get("admin_authenticated") is True


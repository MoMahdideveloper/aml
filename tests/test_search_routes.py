"""Search HTTP routes."""

from sqlalchemy_models import Customer, User


def _user(db, username="search_agent", role="agent"):
    u = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username,
        role=role,
        is_active=True,
    )
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u


def _login(client, username="search_agent"):
    return client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
        follow_redirects=False,
    )


def test_anonymous_api_denied(client, db_setup, app):
    r = client.get("/api/search?q=ada")
    assert r.status_code == 401


def test_anonymous_page_redirect(client, db_setup, app):
    r = client.get("/search?q=ada", follow_redirects=False)
    assert r.status_code in (301, 302)
    assert "/auth/login" in (r.headers.get("Location") or "")


def test_api_and_page_authenticated(client, db_setup, app):
    with app.app_context():
        from database import db

        _user(db)
        db.session.add(
            Customer(
                name="Route Ada",
                email="route.ada@example.com",
                phone="5554000001",
            )
        )
        db.session.commit()
    _login(client)
    r = client.get("/api/search?q=Route")
    assert r.status_code == 200
    data = r.get_json()
    assert "groups" in data
    assert data["total_count"] >= 1
    # no stack traces
    assert "Traceback" not in r.get_data(as_text=True)

    r2 = client.get("/search?q=Route")
    assert r2.status_code == 200
    assert b"Route Ada" in r2.data or b"Results" in r2.data


def test_malformed_api(client, db_setup, app):
    with app.app_context():
        from database import db

        _user(db)
    _login(client)
    r = client.get("/api/search?q=x")
    assert r.status_code == 400
    assert r.get_json()["error"] == "too_short"


def test_flag_off_404(client, db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_GLOBAL_SEARCH", "0")
    # app config already loaded — set on app
    app.config["ENABLE_GLOBAL_SEARCH"] = False
    with app.app_context():
        from database import db

        _user(db)
    _login(client)
    # feature_enabled reads env
    import services.unified_search as us

    monkeypatch.setattr(us, "feature_enabled", lambda: False)
    r = client.get("/api/search?q=hello")
    assert r.status_code == 404

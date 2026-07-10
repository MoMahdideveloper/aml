"""Context API auth and flag gates."""

from sqlalchemy_models import Customer, User


def test_flag_off_returns_404(client, db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "0")
    # rebuild config on app
    app.config["ENABLE_AI_CONTEXT"] = False
    r = client.get("/api/context/customer/1")
    assert r.status_code == 404


def test_anonymous_401_when_enabled(client, db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    app.config["ENABLE_AI_CONTEXT"] = True
    r = client.get("/api/context/customer/1")
    assert r.status_code == 401


def test_staff_gets_packet(client, db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_AI_CONTEXT", "1")
    app.config["ENABLE_AI_CONTEXT"] = True
    with app.app_context():
        from database import db

        c = Customer(
            name="Route Ctx",
            email="routectx@example.com",
            phone="5553000099",
        )
        db.session.add(c)
        db.session.commit()
        cid = c.id
        u = User(
            username="ctxstaff",
            email="ctxstaff@example.com",
            full_name="Ctx",
            role="agent",
            is_active=True,
        )
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()

    client.post(
        "/auth/login",
        data={"username": "ctxstaff", "password": "password123"},
    )
    r = client.get(f"/api/context/customer/{cid}?purpose=brief")
    assert r.status_code == 200
    data = r.get_json()
    assert data["entity_type"] == "customer"
    assert data["entity_id"] == cid
    assert "sections" in data

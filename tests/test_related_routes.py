"""Related API permissions and flag."""

from sqlalchemy_models import Customer, Deal, Property, User


def test_related_flag_off_404(client, db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_DERIVED_EDGES", "0")
    app.config["ENABLE_DERIVED_EDGES"] = False
    r = client.get("/api/related/customer/1")
    assert r.status_code == 404


def test_related_auth_and_success(client, db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_DERIVED_EDGES", "1")
    app.config["ENABLE_DERIVED_EDGES"] = True
    with app.app_context():
        from database import db

        c = Customer(name="Rel C", email="relc@example.com", phone="5554000020")
        p = Property(title="Rel P", address="A", property_type="villa", price=1)
        db.session.add_all([c, p])
        db.session.flush()
        db.session.add(Deal(customer_id=c.id, property_id=p.id, status="prospecting"))
        u = User(
            username="relstaff",
            email="relstaff@example.com",
            full_name="R",
            role="agent",
            is_active=True,
        )
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
        cid = c.id

    r = client.get(f"/api/related/customer/{cid}")
    assert r.status_code == 401

    client.post("/auth/login", data={"username": "relstaff", "password": "password123"})
    r2 = client.get(f"/api/related/customer/{cid}")
    assert r2.status_code == 200
    data = r2.get_json()
    assert data["entity_type"] == "customer"
    assert "neighbors" in data

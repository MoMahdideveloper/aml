"""Customer 360 HTTP routes."""

from sqlalchemy_models import Customer, User


def _setup(db):
    u = User(
        username="c360",
        email="c360@example.com",
        full_name="C360",
        role="agent",
        is_active=True,
    )
    u.set_password("password123")
    c = Customer(name="Route Cust", email="rc@example.com", phone="5559200001")
    db.session.add_all([u, c])
    db.session.commit()
    return c


def test_anonymous_redirect(client, db_setup, app):
    r = client.get("/customers/1", follow_redirects=False)
    assert r.status_code in (301, 302)


def test_log_note_and_view(client, db_setup, app):
    with app.app_context():
        from database import db

        c = _setup(db)
        cid = c.id
    client.post("/auth/login", data={"username": "c360", "password": "password123"})
    r = client.get(f"/customers/{cid}")
    assert r.status_code == 200
    assert b"Customer 360" in r.data or b"Activity timeline" in r.data

    r2 = client.post(
        f"/customers/{cid}/interactions",
        data={
            "interaction_type": "note",
            "subject": "Visit",
            "body": "Discussed budget",
        },
        follow_redirects=True,
    )
    assert r2.status_code == 200
    assert b"Visit" in r2.data
    assert b"Discussed budget" in r2.data


def test_xss_escaped(client, db_setup, app):
    with app.app_context():
        from database import db

        c = _setup(db)
        cid = c.id
    client.post("/auth/login", data={"username": "c360", "password": "password123"})
    client.post(
        f"/customers/{cid}/interactions",
        data={
            "interaction_type": "note",
            "subject": "xss",
            "body": "<script>alert(1)</script>",
        },
        follow_redirects=True,
    )
    r = client.get(f"/customers/{cid}")
    assert b"<script>alert(1)</script>" not in r.data
    assert b"&lt;script&gt;" in r.data or b"alert" in r.data

"""Search permission / enumeration basics."""

from sqlalchemy_models import Customer, User


def test_other_user_saved_view_404(client, db_setup, app):
    with app.app_context():
        from database import db
        from services.saved_views_service import saved_views_service

        u1 = User(
            username="p1",
            email="p1@example.com",
            full_name="p1",
            role="agent",
            is_active=True,
        )
        u1.set_password("password123")
        u2 = User(
            username="p2",
            email="p2@example.com",
            full_name="p2",
            role="agent",
            is_active=True,
        )
        u2.set_password("password123")
        db.session.add_all([u1, u2])
        db.session.commit()
        v = saved_views_service.create(
            user_id=u1.id,
            name="Secret",
            entity_scope="customers",
            filters={"q": "x"},
        )
        vid = v.id

    client.post("/auth/login", data={"username": "p2", "password": "password123"})
    r = client.get(f"/search/views/{vid}/apply", follow_redirects=False)
    assert r.status_code == 404


def test_deleted_not_in_counts(client, db_setup, app):
    with app.app_context():
        from database import db

        u = User(
            username="p3",
            email="p3@example.com",
            full_name="p3",
            role="agent",
            is_active=True,
        )
        u.set_password("password123")
        db.session.add(u)
        db.session.add(
            Customer(
                name="Hidden Del",
                email="hdel@example.com",
                phone="5556000001",
                is_deleted=True,
            )
        )
        db.session.commit()
    client.post("/auth/login", data={"username": "p3", "password": "password123"})
    r = client.get("/api/search?q=Hidden")
    assert r.status_code == 200
    assert r.get_json()["total_count"] == 0

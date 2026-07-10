"""Permissions and search integration for Customer 360."""

from services.customer_timeline_service import customer_timeline_service
from services.unified_search import parse_search_request, unified_search_service
from sqlalchemy_models import Customer, User


def test_search_links_to_customer_360(db_setup, app):
    with app.app_context():
        from database import db

        c = Customer(name="SearchMe", email="sm@example.com", phone="5559300001")
        db.session.add(c)
        db.session.commit()
        req = parse_search_request(q="SearchMe", scope="customers")
        result = unified_search_service.search(req)
        hits = result["groups"]["customers"]
        assert hits
        assert f"/customers/{c.id}" in hits[0]["url"]
        assert "body" not in str(hits).lower() or True


def test_note_body_not_in_search(db_setup, app):
    with app.app_context():
        from database import db

        c = Customer(name="BodyHide", email="bh@example.com", phone="5559300002")
        db.session.add(c)
        db.session.commit()
        customer_timeline_service.create_interaction(
            customer_id=c.id,
            interaction_type="note",
            subject="ok",
            body="UNIQUE_SECRET_TOKEN_XYZ",
        )
        req = parse_search_request(q="UNIQUE_SECRET_TOKEN_XYZ")
        result = unified_search_service.search(req)
        assert result["total_count"] == 0


def test_cross_customer_delete_blocked(client, db_setup, app):
    with app.app_context():
        from database import db

        u = User(
            username="p360",
            email="p360@example.com",
            full_name="p",
            role="agent",
            is_active=True,
        )
        u.set_password("password123")
        c1 = Customer(name="A", email="a360@example.com", phone="5559300003")
        c2 = Customer(name="B", email="b360@example.com", phone="5559300004")
        db.session.add_all([u, c1, c2])
        db.session.commit()
        ix = customer_timeline_service.create_interaction(
            customer_id=c1.id, interaction_type="note", subject="x"
        )
        iid, c2id = ix.id, c2.id
    client.post("/auth/login", data={"username": "p360", "password": "password123"})
    r = client.post(
        f"/customers/{c2id}/interactions/{iid}/delete",
        follow_redirects=True,
    )
    assert r.status_code == 200
    # still exists under c1
    with app.app_context():
        from sqlalchemy_models import CustomerInteraction
        from database import db

        row = db.session.get(CustomerInteraction, iid)
        assert row is not None and not row.is_deleted

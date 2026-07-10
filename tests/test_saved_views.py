"""Saved views ownership and customer slice."""

import json

from services.saved_views_service import SavedViewError, saved_views_service
from sqlalchemy_models import Customer, SavedView, User


def _users(db):
    out = []
    for name in ("sv_a", "sv_b"):
        u = User(
            username=name,
            email=f"{name}@example.com",
            full_name=name,
            role="agent",
            is_active=True,
        )
        u.set_password("password123")
        db.session.add(u)
        out.append(u)
    db.session.commit()
    return out


def test_create_list_apply_delete(db_setup, app):
    with app.app_context():
        from database import db

        a, b = _users(db)
        view = saved_views_service.create(
            user_id=a.id,
            name="Active buyers",
            entity_scope="customers",
            filters={"status": "active", "customer_type": "buyer", "q": "Ada"},
            is_default=True,
        )
        assert view.id
        payload = json.loads(view.filter_json)
        assert payload["v"] == 1
        assert "evil" not in payload
        # ignore unknown keys
        view2 = saved_views_service.create(
            user_id=a.id,
            name="With junk",
            entity_scope="customers",
            filters={"status": "lead", "sql": "DROP TABLE", "q": "x"},
        )
        p2 = json.loads(view2.filter_json)
        assert "sql" not in p2

        listed = saved_views_service.list_for_user(a.id, "customers")
        assert len(listed) >= 2

        # B cannot access A
        try:
            saved_views_service.get_owned(view.id, b.id)
            assert False, "should forbid"
        except SavedViewError as e:
            assert e.code == "forbidden"

        saved_views_service.delete(view.id, a.id)
        assert db.session.get(SavedView, view.id) is None


def test_routes_saved_view_customer_slice(client, db_setup, app):
    with app.app_context():
        from database import db

        a, _ = _users(db)
        db.session.add(
            Customer(
                name="View Target",
                email="view.target@example.com",
                phone="5555000001",
                status="active",
                customer_type="buyer",
            )
        )
        db.session.commit()
        view = saved_views_service.create(
            user_id=a.id,
            name="Buyers",
            entity_scope="customers",
            filters={"customer_type": "buyer"},
        )
        vid = view.id

    client.post(
        "/auth/login",
        data={"username": "sv_a", "password": "password123"},
    )
    r = client.get(f"/search/views/{vid}/apply", follow_redirects=False)
    assert r.status_code in (301, 302)
    loc = r.headers.get("Location") or ""
    assert "/customers" in loc
    assert "customer_type=buyer" in loc or "buyer" in loc

    r2 = client.get("/customers?customer_type=buyer&search=View")
    assert r2.status_code == 200
    assert b"View Target" in r2.data

    # delete via POST
    r3 = client.post(
        "/search/views",
        data={
            "action": "delete",
            "view_id": str(vid),
            "entity_scope": "customers",
        },
        follow_redirects=True,
    )
    assert r3.status_code == 200

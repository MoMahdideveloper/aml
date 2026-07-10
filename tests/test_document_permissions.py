"""Document HTTP auth."""

import io

from sqlalchemy_models import Customer, Deal, Property, User
from werkzeug.datastructures import FileStorage


def test_anonymous_denied(client, db_setup, app):
    r = client.get("/deals/1/documents", follow_redirects=False)
    assert r.status_code in (301, 302)
    r2 = client.get("/documents/1/download", follow_redirects=False)
    assert r2.status_code in (301, 302, 403, 404)


def test_agent_can_list_and_upload(client, db_setup, app, tmp_path, monkeypatch):
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "docs"))
    with app.app_context():
        from database import db

        u = User(
            username="docag",
            email="docag@example.com",
            full_name="D",
            role="agent",
            is_active=True,
        )
        u.set_password("password123")
        p = Property(title="P", address="1", property_type="apt", price=1)
        c = Customer(name="C", email="dp@example.com", phone="5559700001")
        db.session.add_all([u, p, c])
        db.session.flush()
        deal = Deal(property_id=p.id, customer_id=c.id, status="prospecting", offer_amount=1)
        db.session.add(deal)
        db.session.commit()
        did = deal.id

    client.post("/auth/login", data={"username": "docag", "password": "password123"})
    r = client.get(f"/deals/{did}/documents")
    assert r.status_code == 200
    assert b"Upload" in r.data

    data = {
        "category": "contract",
        "display_name": "Test PDF",
        "file": (io.BytesIO(b"%PDF-1.4\nhello\n%%EOF\n"), "t.pdf"),
    }
    r2 = client.post(
        f"/deals/{did}/documents",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert r2.status_code == 200
    assert b"Test PDF" in r2.data or b"available" in r2.data

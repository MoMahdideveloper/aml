"""Import HTTP routes: auth, upload→map→preview, isolation, error export."""

from __future__ import annotations

import io

import pytest
from sqlalchemy_models import Customer, ImportBatch, User


def _seed_users(db):
    for username, email, role in (
        ("imp_agent", "imp_agent@example.com", "agent"),
        ("imp_agent2", "imp_agent2@example.com", "agent"),
        ("imp_viewer", "imp_viewer@example.com", "viewer"),
    ):
        u = User(
            username=username,
            email=email,
            full_name=username,
            role=role,
            is_active=True,
        )
        u.set_password("password123")
        db.session.add(u)
    db.session.commit()


def _login(client, username="imp_agent"):
    return client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
        follow_redirects=False,
    )


def test_anonymous_redirected(client, db_setup, app):
    r = client.get("/imports/")
    assert r.status_code in (301, 302)
    assert "/auth/login" in (r.headers.get("Location") or "")


def test_viewer_denied(client, db_setup, app):
    with app.app_context():
        from database import db

        _seed_users(db)
    _login(client, "imp_viewer")
    r = client.get("/imports/", follow_redirects=False)
    assert r.status_code in (301, 302)
    # flash + redirect away from imports
    assert "/imports" not in (r.headers.get("Location") or "") or "upload" not in (
        r.headers.get("Location") or ""
    )


def test_upload_map_preview_execute_flow(client, db_setup, app):
    with app.app_context():
        from database import db

        _seed_users(db)
    _login(client)
    # upload page
    assert client.get("/imports/upload").status_code == 200

    csv_data = b"name,email,phone\nRoute User,route.user@example.com,5551112222\n"
    r = client.post(
        "/imports/upload",
        data={
            "entity_type": "customer",
            "file": (io.BytesIO(csv_data), "customers.csv"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert r.status_code in (301, 302)
    loc = r.headers.get("Location") or ""
    assert "/map" in loc
    batch_id = int(loc.rstrip("/").split("/")[-2])

    # map required fields
    r2 = client.post(
        f"/imports/{batch_id}/map",
        data={
            "map_name": "name",
            "map_email": "email",
            "map_phone": "phone",
        },
        follow_redirects=False,
    )
    assert r2.status_code in (301, 302)
    assert "preview" in (r2.headers.get("Location") or "")

    r3 = client.get(f"/imports/{batch_id}/preview")
    assert r3.status_code == 200
    body = r3.get_data(as_text=True)
    assert "valid" in body.lower() or "Preview" in body

    # no business writes yet
    with app.app_context():
        assert Customer.query.count() == 0

    r4 = client.post(
        f"/imports/{batch_id}/execute",
        data={},
        follow_redirects=False,
    )
    assert r4.status_code in (301, 302)
    with app.app_context():
        c = Customer.query.filter_by(email="route.user@example.com").first()
        assert c is not None
        batch = db.session.get(ImportBatch, batch_id)
        assert batch.status == "completed"
        assert batch.imported_rows == 1


def test_batch_isolation_other_user_forbidden(client, db_setup, app):
    with app.app_context():
        from database import db

        _seed_users(db)
        u1 = User.query.filter_by(username="imp_agent").first()
        batch = ImportBatch(
            entity_type="customer",
            status="uploaded",
            original_filename="x.csv",
            file_hash="deadbeef",
            uploader_id=u1.id,
            mapping_json="{}",
        )
        db.session.add(batch)
        db.session.commit()
        bid = batch.id

    _login(client, "imp_agent2")
    # HTML 403 is converted by error_handlers to flash + redirect
    r = client.get(f"/imports/{bid}/preview", follow_redirects=False)
    assert r.status_code in (302, 403)
    if r.status_code == 302:
        loc = r.headers.get("Location") or ""
        assert f"/imports/{bid}" not in loc
    # JSON/XHR still receives real 403
    r_json = client.get(
        f"/imports/{bid}/preview",
        headers={"X-Requested-With": "XMLHttpRequest"},
        follow_redirects=False,
    )
    assert r_json.status_code == 403


def test_reject_non_csv_upload(client, db_setup, app):
    with app.app_context():
        from database import db

        _seed_users(db)
    _login(client)
    r = client.post(
        "/imports/upload",
        data={
            "entity_type": "customer",
            "file": (io.BytesIO(b"%PDF-1.4 fake"), "evil.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert r.status_code == 200
    assert b"rejected" in r.data.lower() or b"not" in r.data.lower()


def test_error_export_formula_neutralized(client, db_setup, app):
    with app.app_context():
        from database import db

        _seed_users(db)
        u = User.query.filter_by(username="imp_agent").first()
        batch = ImportBatch(
            entity_type="customer",
            status="previewed",
            original_filename="e.csv",
            file_hash="ff",
            uploader_id=u.id,
            mapping_json="{}",
        )
        db.session.add(batch)
        db.session.flush()
        from sqlalchemy_models import ImportRowResult

        db.session.add(
            ImportRowResult(
                batch_id=batch.id,
                row_number=1,
                outcome="invalid",
                error_codes="email_invalid",
                diagnostic="=cmd|'/c calc'!A0",
            )
        )
        db.session.commit()
        bid = batch.id

    _login(client)
    r = client.get(f"/imports/{bid}/errors.csv")
    assert r.status_code == 200
    text = r.get_data(as_text=True)
    assert "'=cmd" in text or text.count("=") == 0
    assert "email_invalid" in text


def test_rollback_route_requires_confirm(client, db_setup, app):
    with app.app_context():
        from database import db
        from services.import_parser import parse_csv_bytes
        from services.import_service import ImportService
        from pathlib import Path

        _seed_users(db)
        u = User.query.filter_by(username="imp_agent").first()
        csv_bytes = b"name,email,phone\nRb Route,rb.route@example.com,5553334444\n"
        parsed = parse_csv_bytes(csv_bytes)
        path = Path("instance/imports") / f"route_{parsed.file_hash[:10]}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(csv_bytes)
        batch = ImportBatch(
            entity_type="customer",
            status="mapped",
            original_filename="r.csv",
            file_hash=parsed.file_hash,
            uploader_id=u.id,
            mapping_json='{"name":"name","email":"email","phone":"phone"}',
            temp_path=str(path),
        )
        db.session.add(batch)
        db.session.commit()
        svc = ImportService()
        svc.run_preview(batch)
        svc.execute(batch)
        bid = batch.id

    _login(client)
    r = client.post(
        f"/imports/{bid}/rollback",
        data={},
        follow_redirects=True,
    )
    assert r.status_code == 200
    with app.app_context():
        c = Customer.query.filter_by(email="rb.route@example.com").first()
        assert c is not None and c.is_deleted is False

    r2 = client.post(
        f"/imports/{bid}/rollback",
        data={"confirm": "yes"},
        follow_redirects=True,
    )
    assert r2.status_code == 200
    with app.app_context():
        c = Customer.query.filter_by(email="rb.route@example.com").first()
        assert c is not None and c.is_deleted is True

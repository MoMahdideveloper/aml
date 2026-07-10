"""Sales report HTTP routes."""

from sqlalchemy_models import User


def _user(db, username="rep_agent", role="agent"):
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


def _login(client, username="rep_agent"):
    return client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )


def test_anonymous_redirect(client, db_setup, app):
    r = client.get("/reports/sales", follow_redirects=False)
    assert r.status_code in (301, 302)
    assert "/auth/login" in (r.headers.get("Location") or "")


def test_viewer_denied(client, db_setup, app):
    with app.app_context():
        from database import db

        _user(db, "viewer_r", "viewer")
    _login(client, "viewer_r")
    r = client.get("/reports/sales", follow_redirects=False)
    assert r.status_code in (301, 302)


def test_agent_report_and_export(client, db_setup, app):
    with app.app_context():
        from database import db

        _user(db)
    _login(client)
    r = client.get("/reports/sales?days=30")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert "Weighted forecast" in body or "pipeline" in body.lower()
    assert "Pipeline by stage" in body

    r2 = client.get("/reports/sales/export.csv?days=30")
    assert r2.status_code == 200
    assert "text/csv" in (r2.headers.get("Content-Type") or "")
    text = r2.get_data(as_text=True)
    assert "summary" in text
    assert "Traceback" not in text


def test_invalid_period(client, db_setup, app):
    with app.app_context():
        from database import db

        _user(db)
    _login(client)
    r = client.get(
        "/reports/sales?start=2026-06-01&end=2026-01-01",
        follow_redirects=True,
    )
    assert r.status_code == 200

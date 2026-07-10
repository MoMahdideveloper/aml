"""Automation admin routes require auth."""

from sqlalchemy_models import User


def test_anonymous_admin_automations_denied(client, db_setup, app):
    r = client.get("/admin/automations", follow_redirects=False)
    assert r.status_code in (301, 302, 401, 403)


def test_agent_session_cannot_use_admin_api(client, db_setup, app):
    with app.app_context():
        from database import db

        u = User(
            username="auto_agent",
            email="auto_agent@example.com",
            full_name="aa",
            role="agent",
            is_active=True,
        )
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
    client.post(
        "/auth/login",
        data={"username": "auto_agent", "password": "password123"},
    )
    r = client.get("/api/automations/rules")
    assert r.status_code in (301, 302, 401, 403)

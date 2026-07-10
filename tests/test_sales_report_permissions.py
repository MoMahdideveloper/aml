"""Sales report permission edges."""

from sqlalchemy_models import User


def test_flag_off_404(client, db_setup, app, monkeypatch):
    import views.reports as reports_views

    monkeypatch.setattr(reports_views, "feature_enabled", lambda: False)
    with app.app_context():
        from database import db

        u = User(
            username="f1",
            email="f1@example.com",
            full_name="f1",
            role="agent",
            is_active=True,
        )
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
    client.post("/auth/login", data={"username": "f1", "password": "password123"})
    assert client.get("/reports/sales").status_code == 404
    assert client.get("/reports/sales/export.csv").status_code == 404

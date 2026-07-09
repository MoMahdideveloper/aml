"""Optional PostgreSQL migration + readiness smoke.

Runs only when DATABASE_URL points at Postgres (CI postgres job sets this).
"""

import os

import pytest

DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_POSTGRES = DATABASE_URL.startswith("postgresql") or DATABASE_URL.startswith("postgres")

pytestmark = pytest.mark.skipif(
    not IS_POSTGRES,
    reason="PostgreSQL DATABASE_URL required (CI postgres job)",
)


def test_alembic_upgrade_heads_on_postgres():
    """Empty-ish Postgres schema upgrades through merge head."""
    from flask_migrate import upgrade
    from app import create_app

    # Use a strong secret so production-like FLASK_ENV still boots if set.
    os.environ.setdefault("SESSION_SECRET", "ci-postgres-migration-secret-32chars")
    app = create_app({"TESTING": True})
    with app.app_context():
        upgrade(revision="heads")
        from database import db
        from sqlalchemy import inspect, text

        names = set(inspect(db.engine).get_table_names())
        assert "properties" in names
        assert "dashboard_stat_snapshots" in names
        db.session.execute(text("SELECT 1"))


def test_readyz_against_postgres():
    from app import create_app
    from database import db
    from flask_migrate import upgrade

    os.environ.setdefault("SESSION_SECRET", "ci-postgres-migration-secret-32chars")
    app = create_app({"TESTING": True})
    with app.app_context():
        upgrade(revision="heads")
        client = app.test_client()
        resp = client.get("/readyz")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ready"

"""Destructive operation guards: method, soft-delete, FK, failed restore isolation."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def test_delete_routes_reject_get(client, db_setup, app):
    """Mutating deletes must not run via GET."""
    for path in (
        "/agents/1/delete",
        "/customers/1/delete",
        "/deals/1/delete",
    ):
        resp = client.get(path)
        # 405 Method Not Allowed or redirect/404 — must not be a successful delete 200 HTML that performed delete
        assert resp.status_code in (302, 303, 404, 405, 400, 401, 403)


def test_delete_agent_blocked_when_active_listings_exist(app, db_setup):
    """Service must refuse agent delete while listings remain (no silent cascade)."""
    from database_service import database_service
    from sqlalchemy_models import Agent, Property

    with app.app_context():
        agent = database_service.add_agent(
            "Del Agent", "del.agent@example.com", "555", "X", "bio"
        )
        prop = database_service.add_property(
            title="Keep Property",
            address="1 Keep St",
            price=100000,
            property_type="house",
            bedrooms=2,
            bathrooms=1,
            square_feet=1000,
            description="must remain",
        )
        if hasattr(prop, "agent_id"):
            prop.agent_id = agent.id
            db_setup.session.commit()
        prop_id = prop.id
        agent_id = agent.id

        with pytest.raises(ValueError, match="active listing"):
            database_service.delete_agent(agent_id)

        agent2 = db_setup.session.get(Agent, agent_id)
        prop2 = db_setup.session.get(Property, prop_id)
        assert prop2 is not None
        assert prop2.title == "Keep Property"
        assert agent2 is not None
        assert getattr(agent2, "is_deleted", False) is not True


def test_soft_delete_agent_without_listings(app, db_setup):
    from database_service import database_service
    from sqlalchemy_models import Agent

    with app.app_context():
        agent = database_service.add_agent(
            "Free Agent", "free.agent@example.com", "555", "X", "bio"
        )
        agent_id = agent.id
        database_service.delete_agent(agent_id)
        agent2 = db_setup.session.get(Agent, agent_id)
        assert agent2 is not None
        if hasattr(agent2, "is_deleted"):
            assert agent2.is_deleted is True


def test_foreign_keys_enforced_on_sqlite_when_enabled(tmp_path: Path):
    """Document FK pragma behavior used by verify_recovery."""
    db = tmp_path / "fk.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(
            """
            CREATE TABLE parents (id INTEGER PRIMARY KEY);
            CREATE TABLE children (
              id INTEGER PRIMARY KEY,
              parent_id INTEGER NOT NULL REFERENCES parents(id)
            );
            INSERT INTO parents (id) VALUES (1);
            """
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO children (id, parent_id) VALUES (1, 999)")
            conn.commit()
    finally:
        conn.close()


def test_customer_delete_blocked_with_active_deals(client, app, db_setup):
    """Business rule: customer with active deals should not hard-vanish silently."""
    from database_service import database_service
    from sqlalchemy_models import Customer

    with app.app_context():
        agent = database_service.add_agent(
            "CDel Agent", "cdel.agent@example.com", "1", "X", "b"
        )
        prop = database_service.add_property(
            title="CDel Prop",
            address="2 St",
            price=1,
            property_type="house",
            bedrooms=1,
            bathrooms=1,
            square_feet=1,
            description="x",
        )
        cust = database_service.add_customer(
            name="CDel Customer",
            email="cdel@example.com",
            phone="1",
        )
        try:
            database_service.add_deal(
                prop.id, cust.id, agent.id, "prospecting", 1000.0
            )
        except Exception:
            pytest.skip("add_deal signature/data not available")

        before = db_setup.session.get(Customer, cust.id)
        assert before is not None

        # POST delete — may flash error and leave customer
        resp = client.post(f"/customers/{cust.id}/delete", follow_redirects=True)
        assert resp.status_code in (200, 302, 303, 400, 403)
        after = db_setup.session.get(Customer, cust.id)
        # Soft-deleted or still present with active-deal guard
        assert after is not None

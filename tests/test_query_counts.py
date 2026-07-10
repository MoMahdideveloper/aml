"""Route SQL query budgets for list/dashboard pages (catch N+1 regressions)."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.engine import Engine


def _count_queries(app, path: str) -> int:
    statements: list[str] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(Engine, "before_cursor_execute", before_cursor_execute)
    try:
        client = app.test_client()
        resp = client.get(path)
        assert resp.status_code < 400, f"{path} -> {resp.status_code}"
        return len(statements)
    finally:
        event.remove(Engine, "before_cursor_execute", before_cursor_execute)


def _seed_list_data(db_setup):
    from database_service import database_service

    agent = database_service.add_agent(
        "Query Count Agent", "qcount.agent@example.com", "555-0101", "Luxury", "bio"
    )
    props = []
    for i in range(4):
        props.append(
            database_service.add_property(
                title=f"QC Prop {i}",
                address=f"{i} Query Ct",
                price=200000 + i,
                property_type="house",
                bedrooms=3,
                bathrooms=2,
                square_feet=1200,
                description="query count seed",
            )
        )
    cust = database_service.add_customer(
        name="QC Customer",
        email="qcount.cust@example.com",
        phone="555-0202",
    )
    if props and cust and agent:
        try:
            database_service.add_deal(
                props[0].id, cust.id, agent.id, "prospecting", 150000.0
            )
        except Exception:
            pass


def test_properties_list_query_budget(app, db_setup):
    """Property list must not issue one images query per card (N+1)."""
    _seed_list_data(db_setup)
    with app.app_context():
        n = _count_queries(app, "/properties")
    # Before fix: ~1 + N image queries. Budget allows filters + one images IN load.
    assert n <= 12, f"/properties ran {n} SQL statements (budget 12)"


def test_dashboard_query_budget(app, db_setup):
    _seed_list_data(db_setup)
    with app.app_context():
        n = _count_queries(app, "/dashboard")
    # Aggregates + snapshot + bounded recent collections; no per-deal relation spam.
    assert n <= 22, f"/dashboard ran {n} SQL statements (budget 22)"


def test_deals_list_query_budget(app, db_setup):
    _seed_list_data(db_setup)
    with app.app_context():
        n = _count_queries(app, "/deals")
    assert n <= 10, f"/deals ran {n} SQL statements (budget 10)"

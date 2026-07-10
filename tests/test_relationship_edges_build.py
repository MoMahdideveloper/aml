"""Relationship edge rebuild from CRM FKs."""

from services.relationship_graph import neighbors, rebuild_for_entity
from sqlalchemy_models import Agent, Customer, Deal, Property, RelationshipEdge


def test_rebuild_customer_deal_property(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_DERIVED_EDGES", "1")
    with app.app_context():
        from database import db

        agent = Agent(name="Graph Agent", email="ga@example.com", phone="5554000001")
        db.session.add(agent)
        db.session.flush()
        c = Customer(name="Graph Cust", email="gc@example.com", phone="5554000002")
        p = Property(
            title="Graph Prop",
            address="1 G",
            property_type="villa",
            price=100,
            agent_id=agent.id,
        )
        db.session.add_all([c, p])
        db.session.flush()
        d = Deal(
            customer_id=c.id,
            property_id=p.id,
            agent_id=agent.id,
            status="prospecting",
            offer_amount=50,
        )
        db.session.add(d)
        db.session.commit()

        result = rebuild_for_entity("customer", c.id)
        assert result["edges_written"] >= 2

        edges = RelationshipEdge.query.all()
        types = {e.edge_type for e in edges}
        assert "customer_deal" in types
        assert "deal_property" in types or "customer_agent" in types

        nb = neighbors("customer", c.id, rebuild_if_empty=False)
        labels = [n["label"] for n in nb["neighbors"]]
        assert any("Deal" in x or "Graph" in x for x in labels)


def test_neighbors_soft_deleted_customer(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_DERIVED_EDGES", "1")
    with app.app_context():
        from database import db

        c = Customer(
            name="Gone",
            email="gone-g@example.com",
            phone="5554000099",
            is_deleted=True,
        )
        db.session.add(c)
        db.session.commit()
        try:
            rebuild_for_entity("customer", c.id)
            assert False, "expected GraphError"
        except Exception as e:
            assert getattr(e, "code", "") == "not_found" or "not found" in str(e).lower()

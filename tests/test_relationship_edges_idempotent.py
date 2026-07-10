"""Rebuild is idempotent (stable edge set)."""

from services.relationship_graph import rebuild_for_entity
from sqlalchemy_models import Agent, Customer, Deal, Property, RelationshipEdge


def test_double_rebuild_same_count(db_setup, app):
    with app.app_context():
        from database import db

        agent = Agent(name="Idem Agent", email="ia@example.com", phone="5554000011")
        db.session.add(agent)
        db.session.flush()
        c = Customer(name="Idem C", email="ic@example.com", phone="5554000012")
        p = Property(
            title="Idem P",
            address="2",
            property_type="house",
            price=1,
            agent_id=agent.id,
        )
        db.session.add_all([c, p])
        db.session.flush()
        db.session.add(
            Deal(
                customer_id=c.id,
                property_id=p.id,
                agent_id=agent.id,
                status="qualified",
            )
        )
        db.session.commit()

        r1 = rebuild_for_entity("customer", c.id)
        count1 = RelationshipEdge.query.count()
        r2 = rebuild_for_entity("customer", c.id)
        count2 = RelationshipEdge.query.count()
        assert count1 == count2
        assert count1 > 0
        # second run still writes (delete+recreate) but stable cardinality
        assert r2["edges_written"] == r1["edges_written"]

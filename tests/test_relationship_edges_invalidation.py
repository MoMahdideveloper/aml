"""Edges invalidate after deal soft-delete + rebuild."""

from services.relationship_graph import neighbors, rebuild_for_entity
from sqlalchemy_models import Customer, Deal, Property, RelationshipEdge


def test_soft_delete_deal_clears_on_rebuild(db_setup, app):
    with app.app_context():
        from database import db

        c = Customer(name="Inv C", email="invc@example.com", phone="5557000010")
        p = Property(title="Inv P", address="A", property_type="villa", price=1)
        db.session.add_all([c, p])
        db.session.flush()
        d = Deal(customer_id=c.id, property_id=p.id, status="prospecting")
        db.session.add(d)
        db.session.commit()

        rebuild_for_entity("customer", c.id)
        assert RelationshipEdge.query.filter_by(edge_type="customer_deal").count() >= 1

        d.is_deleted = True
        db.session.commit()
        rebuild_for_entity("customer", c.id)
        # no active deal → no customer_deal edges
        assert RelationshipEdge.query.filter_by(
            src_type="customer", src_id=c.id, edge_type="customer_deal"
        ).count() == 0

"""customer_matched_property edges from PropertyMatch."""

from services.relationship_graph import rebuild_for_entity
from sqlalchemy_models import Customer, Property, PropertyMatch, RelationshipEdge


def test_match_edge_built(db_setup, app):
    with app.app_context():
        from database import db

        c = Customer(name="ME", email="me@example.com", phone="5558000011")
        p = Property(title="MP", address="A", property_type="house", price=1)
        db.session.add_all([c, p])
        db.session.flush()
        db.session.add(
            PropertyMatch(
                customer_id=c.id,
                property_id=p.id,
                match_score=0.91,
                status="pending",
            )
        )
        db.session.commit()
        rebuild_for_entity("customer", c.id)
        assert (
            RelationshipEdge.query.filter_by(
                edge_type="customer_matched_property",
                src_id=c.id,
                dst_id=p.id,
            ).count()
            >= 1
        )

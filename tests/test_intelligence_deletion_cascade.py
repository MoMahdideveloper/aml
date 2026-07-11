"""Soft-delete propagates into embeddings, occurrences, edges."""

from services.database_service import DatabaseService
from services.intelligence_cleanup import cleanup_property_derived
from sqlalchemy_models import (
    Property,
    PropertyEmbedding,
    RelationshipEdge,
    VocabOccurrence,
)


def test_cleanup_property_derived_direct(db_setup, app):
    with app.app_context():
        from database import db

        p = Property(title="X", address="1", property_type="house", price=1, bedrooms=1)
        db.session.add(p)
        db.session.commit()
        db.session.add(
            PropertyEmbedding(
                property_id=p.id,
                embedding_data="[0.1,0.2]",
                source_hash="abc",
                provider="test",
                dimension=2,
            )
        )
        db.session.add(
            VocabOccurrence(
                entity_type="property",
                entity_id=p.id,
                field="title",
                normalized_key="house",
                status="active",
                confidence=1.0,
            )
        )
        db.session.add(
            RelationshipEdge(
                src_type="property",
                src_id=p.id,
                dst_type="agent",
                dst_id=1,
                edge_type="property_agent",
            )
        )
        db.session.commit()

        summary = cleanup_property_derived(p.id)
        db.session.commit()
        assert summary["embedding_deleted"] is True
        assert summary["occurrences_deactivated"] >= 1
        assert summary["edges_deleted"] >= 1
        assert PropertyEmbedding.query.filter_by(property_id=p.id).first() is None
        occ = VocabOccurrence.query.filter_by(entity_type="property", entity_id=p.id).first()
        assert occ.status == "inactive"
        assert (
            RelationshipEdge.query.filter_by(src_type="property", src_id=p.id).count()
            == 0
        )


def test_delete_property_runs_cleanup(db_setup, app):
    with app.app_context():
        from database import db

        p = Property(title="Y", address="2", property_type="house", price=1, bedrooms=1)
        db.session.add(p)
        db.session.commit()
        db.session.add(
            PropertyEmbedding(
                property_id=p.id,
                embedding_data="[1.0]",
                source_hash="z",
                provider="test",
                dimension=1,
            )
        )
        db.session.commit()
        svc = DatabaseService()
        assert svc.delete_property(p.id) is True
        db.session.commit()
        assert db.session.get(Property, p.id).is_deleted is True
        assert PropertyEmbedding.query.filter_by(property_id=p.id).first() is None

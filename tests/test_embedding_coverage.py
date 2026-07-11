"""Property embedding coverage metrics."""

from services.embedding_coverage import (
    list_properties_missing_embeddings,
    summarize_property_embedding_coverage,
)
from sqlalchemy_models import Property, PropertyEmbedding


def test_coverage_empty_db(db_setup, app):
    with app.app_context():
        s = summarize_property_embedding_coverage()
        assert s["active_properties"] == 0
        assert s["coverage"] == 1.0
        assert s["missing"] == 0


def test_coverage_and_missing_list(db_setup, app):
    with app.app_context():
        from database import db

        a = Property(title="A", address="1", property_type="house", price=1, bedrooms=1)
        b = Property(title="B", address="2", property_type="house", price=1, bedrooms=1)
        deleted = Property(
            title="D",
            address="3",
            property_type="house",
            price=1,
            bedrooms=1,
            is_deleted=True,
        )
        db.session.add_all([a, b, deleted])
        db.session.commit()
        db.session.add(
            PropertyEmbedding(
                property_id=a.id,
                embedding_data="[0.1]",
                source_hash="h",
                provider="test",
                dimension=1,
            )
        )
        db.session.commit()

        s = summarize_property_embedding_coverage()
        assert s["active_properties"] == 2
        assert s["with_embedding"] == 1
        assert s["missing"] == 1
        assert s["coverage"] == 0.5

        missing = list_properties_missing_embeddings(limit=10)
        assert b.id in missing
        assert a.id not in missing
        assert deleted.id not in missing


def test_missing_list_respects_limit(db_setup, app):
    with app.app_context():
        from database import db

        for i in range(5):
            db.session.add(
                Property(
                    title=f"P{i}",
                    address=str(i),
                    property_type="apt",
                    price=1,
                    bedrooms=1,
                )
            )
        db.session.commit()
        ids = list_properties_missing_embeddings(limit=2)
        assert len(ids) == 2

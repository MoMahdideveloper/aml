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


def test_enqueue_missing_returns_ids_without_blocking(db_setup, app, monkeypatch):
    from services import embedding_coverage as ec

    with app.app_context():
        from database import db

        p = Property(title="E", address="9", property_type="house", price=1, bedrooms=1)
        db.session.add(p)
        db.session.commit()

        class _FakeTask:
            def delay(self, *a, **k):
                raise RuntimeError("no broker")

        monkeypatch.setattr(
            "services.celery_tasks.sync_property_embedding_task",
            _FakeTask(),
            raising=False,
        )
        # Import path used inside enqueue may fail import or delay — either is fine
        out = ec.enqueue_missing_property_embeddings(limit=10)
        assert out["missing_selected"] >= 1
        assert p.id in out["property_ids"]
        assert out["enqueued"] == 0
        assert out["status"] in ("broker_unavailable", "ok")

"""Occurrence reindex idempotence and stale marking."""

from services.vocab.occurrences import list_for_entity, reindex_property
from services.vocab.service import vocab_service
from sqlalchemy_models import Property, VocabOccurrence


def test_reindex_idempotent(db_setup, app):
    with app.app_context():
        from database import db

        vocab_service.create_term("villa")
        try:
            vocab_service.create_term("renovated")
        except Exception:
            pass

        p = Property(
            title="Sunny Villa Home",
            address="1",
            property_type="villa",
            price=1,
            description="A renovated villa near park",
            property_features="villa, pool",
        )
        db.session.add(p)
        db.session.commit()

        r1 = reindex_property(p.id, require_lexicon=True)
        c1 = VocabOccurrence.query.filter_by(entity_type="property", entity_id=p.id).count()
        r2 = reindex_property(p.id, require_lexicon=True)
        c2 = VocabOccurrence.query.filter_by(entity_type="property", entity_id=p.id).count()
        assert r1["status"] == "ok"
        assert r2["status"] == "ok"
        assert c1 == c2
        assert c1 >= 1
        items = list_for_entity("property", p.id)
        assert any(i["normalized_key"] in ("villa", "renovated") for i in items)


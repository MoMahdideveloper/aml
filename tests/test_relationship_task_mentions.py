"""Task relates_to and mentions_concept edges."""

from services.relationship_graph import rebuild_for_entity
from services.vocab.occurrences import reindex_property
from services.vocab.service import vocab_service
from sqlalchemy_models import Agent, Property, RelationshipEdge, Task


def test_task_relates_to(db_setup, app):
    with app.app_context():
        from database import db

        a = Agent(name="T Agent", email="ta@example.com", phone="5557000020")
        db.session.add(a)
        db.session.flush()
        t = Task(
            title="Call client",
            agent_id=a.id,
            source_entity_type="property",
            source_entity_id=99,
        )
        db.session.add(t)
        db.session.commit()
        r = rebuild_for_entity("task", t.id)
        assert r["edges_written"] >= 1
        assert RelationshipEdge.query.filter_by(edge_type="task_relates_to").count() >= 1


def test_mentions_concept(db_setup, app, monkeypatch):
    monkeypatch.setenv("ENABLE_VOCAB_OCCURRENCES", "1")
    with app.app_context():
        from database import db

        term = vocab_service.create_term("villa")
        p = Property(
            title="Mentions Villa",
            address="1",
            property_type="villa",
            price=1,
            description="nice villa unit",
        )
        db.session.add(p)
        db.session.commit()
        reindex_property(p.id, require_lexicon=True)
        rebuild_for_entity("property", p.id)
        assert (
            RelationshipEdge.query.filter_by(
                edge_type="entity_mentions_concept",
                dst_type="concept",
                dst_id=term.id,
            ).count()
            >= 1
        )

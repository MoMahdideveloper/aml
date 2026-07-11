"""Vocab occurrence frequency analytics."""

from services.vocab.analytics import top_terms
from services.vocab.service import vocab_service
from sqlalchemy_models import Property, VocabOccurrence


def test_top_terms_excludes_deleted_and_filters_type(db_setup, app):
    with app.app_context():
        from database import db

        vocab_service.create_term("renovated")
        live = Property(
            title="Villa Live",
            address="1",
            property_type="villa",
            price=1,
            bedrooms=3,
            description="renovated kitchen",
        )
        gone = Property(
            title="Villa Gone",
            address="2",
            property_type="villa",
            price=1,
            bedrooms=3,
            is_deleted=True,
        )
        apt = Property(
            title="Apt",
            address="3",
            property_type="apartment",
            price=1,
            bedrooms=2,
        )
        db.session.add_all([live, gone, apt])
        db.session.commit()
        for pid, field in ((live.id, "description"), (gone.id, "description"), (apt.id, "title")):
            db.session.add(
                VocabOccurrence(
                    entity_type="property",
                    entity_id=pid,
                    field=field,
                    normalized_key="renovated",
                    status="active",
                    confidence=1.0,
                    source_hash="x",
                )
            )
        db.session.commit()

        all_rows = top_terms(entity_type="property", limit=10)
        # deleted villa should not inflate count — only live villa + apt = 2
        renov = [r for r in all_rows if r["normalized_key"] == "renovated"]
        assert renov
        assert renov[0]["count"] == 2

        villa_only = top_terms(entity_type="property", property_type="villa", limit=10)
        renov_v = [r for r in villa_only if r["normalized_key"] == "renovated"]
        assert renov_v
        assert renov_v[0]["count"] == 1


def test_admin_analytics_requires_auth(client, db_setup, app):
    r = client.get("/admin/vocab?show_analytics=1", follow_redirects=False)
    assert r.status_code in (301, 302, 401, 403)

"""AI form audit ORM models (no private path leakage in public to_dict)."""

from sqlalchemy_models import (
    AIFormExtraction,
    AIFormMedia,
    AIFormReviewDecision,
    AIFormSuggestion,
)


def test_extraction_to_dict_excludes_private_by_default(db_setup, app):
    with app.app_context():
        from database import db

        ext = AIFormExtraction(
            actor_user_id=1,
            form_name="property",
            status="ready",
            model_id="gemini-test",
            idempotency_key="abc-1",
            input_meta_json='{"bytes":12}',
        )
        db.session.add(ext)
        db.session.flush()
        db.session.add(
            AIFormMedia(
                extraction_id=ext.id,
                storage_key="ab/secret.bin",
                sha256="deadbeef",
                mime_type="image/jpeg",
                byte_size=12,
            )
        )
        db.session.add(
            AIFormSuggestion(
                extraction_id=ext.id,
                field_name="title",
                confidence=0.9,
                action="review",
                raw_value_json='"Villa"',
                normalized_value_json='"Villa"',
            )
        )
        db.session.add(
            AIFormReviewDecision(
                extraction_id=ext.id,
                field_name="title",
                decision="accept",
                actor_user_id=1,
            )
        )
        db.session.commit()

        d = ext.to_dict()
        assert "storage_key" not in d
        assert d["form_name"] == "property"
        assert d["suggestion_count"] == 1
        assert d["media_count"] == 1
        media = AIFormMedia.query.filter_by(extraction_id=ext.id).first()
        md = media.to_dict()
        assert "storage_key" not in md
        assert md["sha256"] == "deadbeef"

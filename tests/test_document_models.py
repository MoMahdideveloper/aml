"""Document model constraints."""

from sqlalchemy_models import Document


def test_document_to_dict_hides_storage_key(db_setup, app):
    with app.app_context():
        from database import db

        d = Document(
            owner_type="deal",
            owner_id=1,
            category="contract",
            display_name="Offer",
            storage_key="abc123.pdf",
            media_type="application/pdf",
            byte_size=10,
            sha256="0" * 64,
            status="available",
            document_group_id="group1",
            version=1,
        )
        db.session.add(d)
        db.session.commit()
        data = d.to_dict()
        assert "storage_key" not in data
        assert "sha256" not in data
        assert data["display_name"] == "Offer"

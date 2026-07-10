"""Archive and version history."""

import io

from services.document_service import DocumentService
from services.document_storage import LocalDocumentStorage
from sqlalchemy_models import Customer, Deal, Property
from werkzeug.datastructures import FileStorage


def test_archive_blocks_download(tmp_path, db_setup, app):
    with app.app_context():
        from database import db
        import pytest
        from services.document_service import DocumentServiceError

        p = Property(title="P", address="1", property_type="apt", price=1)
        c = Customer(name="C", email="dv@example.com", phone="5559600001")
        db.session.add_all([p, c])
        db.session.flush()
        deal = Deal(property_id=p.id, customer_id=c.id, status="prospecting", offer_amount=1)
        db.session.add(deal)
        db.session.commit()
        svc = DocumentService(storage=LocalDocumentStorage(str(tmp_path / "s")))
        doc = svc.upload(
            owner_type="deal",
            owner_id=deal.id,
            file_storage=FileStorage(
                stream=io.BytesIO(b"%PDF-1.4\nx\n%%EOF\n"), filename="a.pdf"
            ),
            category="contract",
        )
        svc.archive(doc.id, actor_id=1, actor_label="t")
        with pytest.raises(DocumentServiceError):
            svc.prepare_download(doc.id, actor_id=1, actor_label="t")

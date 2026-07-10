"""Security abuse cases for document pipeline."""

import io

import pytest
from services.document_service import DocumentService, DocumentServiceError
from services.document_storage import LocalDocumentStorage
from services.document_validation import detect_media_type
from sqlalchemy_models import Customer, Deal, Property
from werkzeug.datastructures import FileStorage


def test_path_traversal_filename_ignored_in_storage(tmp_path, db_setup, app):
    with app.app_context():
        from database import db

        p = Property(title="P", address="1", property_type="apt", price=1)
        c = Customer(name="C", email="ds@example.com", phone="5559800001")
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
                stream=io.BytesIO(b"%PDF-1.4\nx\n%%EOF\n"),
                filename="../../etc/passwd.pdf",
            ),
            category="other",
        )
        assert ".." not in doc.storage_key
        assert "/" not in doc.storage_key
        assert "\\" not in doc.storage_key


def test_svg_rejected():
    assert detect_media_type(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>") is None


def test_executable_magic_rejected(tmp_path, db_setup, app):
    with app.app_context():
        from database import db

        p = Property(title="P", address="1", property_type="apt", price=1)
        c = Customer(name="C", email="ds2@example.com", phone="5559800002")
        db.session.add_all([p, c])
        db.session.flush()
        deal = Deal(property_id=p.id, customer_id=c.id, status="prospecting", offer_amount=1)
        db.session.add(deal)
        db.session.commit()
        svc = DocumentService(storage=LocalDocumentStorage(str(tmp_path / "s")))
        with pytest.raises(DocumentServiceError):
            svc.upload(
                owner_type="deal",
                owner_id=deal.id,
                file_storage=FileStorage(
                    stream=io.BytesIO(b"MZ\x90\x00fakeexe"),
                    filename="virus.pdf",
                ),
                category="other",
            )


def test_missing_owner_404(tmp_path, db_setup, app):
    with app.app_context():
        svc = DocumentService(storage=LocalDocumentStorage(str(tmp_path / "s")))
        with pytest.raises(DocumentServiceError) as e:
            svc.upload(
                owner_type="deal",
                owner_id=999999,
                file_storage=FileStorage(
                    stream=io.BytesIO(b"%PDF-1.4\n"), filename="a.pdf"
                ),
                category="contract",
            )
        assert e.value.http == 404

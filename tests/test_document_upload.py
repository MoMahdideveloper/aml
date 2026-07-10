"""Document upload pipeline."""

import io

import pytest
from services.document_service import DocumentService, DocumentServiceError
from services.document_storage import LocalDocumentStorage
from sqlalchemy_models import Customer, Deal, Document, Property
from werkzeug.datastructures import FileStorage


@pytest.fixture()
def svc(tmp_path, db_setup, app):
    store = LocalDocumentStorage(str(tmp_path / "docs"))
    return DocumentService(storage=store)


def _deal(db):
    p = Property(title="P", address="1", property_type="apt", price=1)
    c = Customer(name="C", email="du@example.com", phone="5559400001")
    db.session.add_all([p, c])
    db.session.flush()
    d = Deal(property_id=p.id, customer_id=c.id, status="prospecting", offer_amount=1)
    db.session.add(d)
    db.session.commit()
    return d


def test_upload_pdf_available(svc, db_setup, app):
    with app.app_context():
        from database import db

        d = _deal(db)
        pdf = b"%PDF-1.4\n%synthetic\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
        fs = FileStorage(stream=io.BytesIO(pdf), filename="contract.pdf", content_type="application/pdf")
        doc = svc.upload(
            owner_type="deal",
            owner_id=d.id,
            file_storage=fs,
            category="contract",
            display_name="Contract v1",
            actor_label="tester",
        )
        assert doc.status == "available"
        assert doc.version == 1
        assert Document.query.count() == 1


def test_reject_html_as_pdf(svc, db_setup, app):
    with app.app_context():
        from database import db

        d = _deal(db)
        data = b"<html><body>hi</body></html>"
        fs = FileStorage(stream=io.BytesIO(data), filename="evil.pdf", content_type="application/pdf")
        with pytest.raises(DocumentServiceError) as e:
            svc.upload(
                owner_type="deal",
                owner_id=d.id,
                file_storage=fs,
                category="contract",
            )
        assert e.value.code in ("unsupported_type", "bad_pdf")
        assert Document.query.count() == 0


def test_eicar_quarantined(svc, db_setup, app):
    with app.app_context():
        from database import db
        from services.document_validation import EICAR_MARKER

        d = _deal(db)
        data = b"%PDF-1.4\n" + EICAR_MARKER + b"\n%%EOF\n"
        fs = FileStorage(stream=io.BytesIO(data), filename="bad.pdf")
        doc = svc.upload(
            owner_type="deal",
            owner_id=d.id,
            file_storage=fs,
            category="other",
        )
        assert doc.status == "quarantined"


def test_version_increments(svc, db_setup, app):
    with app.app_context():
        from database import db

        d = _deal(db)
        pdf1 = b"%PDF-1.4\nv1\n%%EOF\n"
        pdf2 = b"%PDF-1.4\nv2 content\n%%EOF\n"
        fs1 = FileStorage(stream=io.BytesIO(pdf1), filename="a.pdf")
        doc1 = svc.upload(
            owner_type="deal",
            owner_id=d.id,
            file_storage=fs1,
            category="offer",
        )
        fs2 = FileStorage(stream=io.BytesIO(pdf2), filename="a.pdf")
        doc2 = svc.upload(
            owner_type="deal",
            owner_id=d.id,
            file_storage=fs2,
            category="offer",
            replace_group_id=doc1.document_group_id,
        )
        assert doc2.version == 2
        assert doc2.is_latest
        db.session.refresh(doc1)
        assert not doc1.is_latest

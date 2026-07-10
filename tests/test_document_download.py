"""Download authorization and status gates."""

import io

import pytest
from services.document_service import DocumentService, DocumentServiceError
from services.document_storage import LocalDocumentStorage
from sqlalchemy_models import Customer, Deal, Property
from werkzeug.datastructures import FileStorage


def _svc(tmp_path):
    return DocumentService(storage=LocalDocumentStorage(str(tmp_path / "d")))


def test_quarantine_cannot_download(tmp_path, db_setup, app):
    with app.app_context():
        from database import db
        from services.document_validation import EICAR_MARKER

        p = Property(title="P", address="1", property_type="apt", price=1)
        c = Customer(name="C", email="dd@example.com", phone="5559500001")
        db.session.add_all([p, c])
        db.session.flush()
        deal = Deal(property_id=p.id, customer_id=c.id, status="prospecting", offer_amount=1)
        db.session.add(deal)
        db.session.commit()
        svc = _svc(tmp_path)
        data = b"%PDF-1.4\n" + EICAR_MARKER + b"\n"
        doc = svc.upload(
            owner_type="deal",
            owner_id=deal.id,
            file_storage=FileStorage(stream=io.BytesIO(data), filename="x.pdf"),
            category="other",
        )
        with pytest.raises(DocumentServiceError) as e:
            svc.prepare_download(doc.id, actor_id=1, actor_label="t")
        assert e.value.code == "not_available"


def test_available_download_streams(tmp_path, db_setup, app):
    with app.app_context():
        from database import db

        p = Property(title="P2", address="2", property_type="apt", price=1)
        c = Customer(name="C2", email="dd2@example.com", phone="5559500002")
        db.session.add_all([p, c])
        db.session.flush()
        deal = Deal(property_id=p.id, customer_id=c.id, status="prospecting", offer_amount=1)
        db.session.add(deal)
        db.session.commit()
        svc = _svc(tmp_path)
        payload = b"%PDF-1.4\nok\n%%EOF\n"
        doc = svc.upload(
            owner_type="deal",
            owner_id=deal.id,
            file_storage=FileStorage(stream=io.BytesIO(payload), filename="ok.pdf"),
            category="contract",
        )
        d, fh, disp = svc.prepare_download(doc.id, actor_id=1, actor_label="t")
        assert d.id == doc.id
        assert fh.read() == payload
        fh.close()
        assert disp == "attachment"

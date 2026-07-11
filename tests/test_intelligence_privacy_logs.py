"""Privacy: search/context paths must not log raw query or packet bodies."""

import logging

from services.unified_search import parse_search_request, unified_search_service
from sqlalchemy_models import Property


class _CapturingHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def test_search_completed_log_omits_raw_query(db_setup, app, monkeypatch, caplog):
    monkeypatch.setenv("ENABLE_CUSTOMER_NL_FILTERS", "0")
    secret = "zzUNIQUESECRETQUERY999"
    with app.app_context():
        from database import db

        db.session.add(
            Property(
                title="Normal Home",
                address="1",
                property_type="house",
                price=1,
                bedrooms=1,
            )
        )
        db.session.commit()
        with caplog.at_level(logging.DEBUG):
            req = parse_search_request(q=secret, scope="properties", mode="full")
            unified_search_service.search(req)
        blob = "\n".join(caplog.messages)
        assert secret not in blob


def test_hybrid_meta_no_raw_query_in_log(db_setup, app, monkeypatch, caplog):
    monkeypatch.setenv("ENABLE_HYBRID_SEARCH", "1")
    secret = "yyHYBRIDPRIVACYQUERY888"
    with app.app_context():
        from services.hybrid_search import HybridSearchService

        with caplog.at_level(logging.DEBUG):
            req = parse_search_request(q=secret, scope="properties", mode="full")
            HybridSearchService().search(req)
        blob = "\n".join(caplog.messages)
        assert secret not in blob

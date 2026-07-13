"""Integration-level proof: provider extraction failure is bounded and safe.

Contract under test:
  1. Provider exception → HTTP response is safe JSON (no traceback, no exception text).
  2. Provider exception → no CRM entity (Property/Customer) is created.
  3. Degraded/timeout extraction result → bounded response, no CRM entity.
  4. Malformed provider response → bounded degraded response, no CRM entity.
  5. Manual Property save succeeds after a failed AI extraction (cross-request isolation).

These tests use zero network, zero live provider, and disposable pytest fixtures only.
"""

from __future__ import annotations

import json

import pytest

from services.ai_form_assist.gemini_extractor import ExtractionError, GeminiFormExtractor
from services.ai_form_assist.service import AIFormAssistService
from services.ai_form_assist.storage import PrivateAuditStorage
from services.ai_form_assist.types import ExtractionResult, SourceType
from sqlalchemy_models import Customer, Property, User


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class _BrokenExtractor:
    """Extractor that raises directly — bypasses extractor's own error handling."""

    def __init__(self, exc: Exception | None = None):
        self._exc = exc or RuntimeError("provider blew up: internal details SHOULD NOT APPEAR")

    def extract(self, **kwargs) -> ExtractionResult:  # noqa: ANN001
        raise self._exc

    def escalate_uncertain(self, **kwargs) -> ExtractionResult:  # noqa: ANN001
        raise self._exc


class _DegradedExtractor:
    """Extractor that returns a degraded ExtractionResult (provider timeout)."""

    def __init__(self, error_code: str = "timeout"):
        self.error_code = error_code

    def extract(self, *, form: str, **kwargs) -> ExtractionResult:
        return ExtractionResult(
            form=form,
            source_type=SourceType.text,
            suggestions=[],
            model_id="test-model",
            degraded=True,
            error=self.error_code,
        )

    def escalate_uncertain(self, *, form: str, **kwargs) -> ExtractionResult:
        return self.extract(form=form)


class _MalformedResponseExtractor:
    """Extractor backed by a client whose generate_content returns unparseable garbage."""

    class _Models:
        def generate_content(self, **kwargs):
            return type("R", (), {"text": "NOT JSON AT ALL }{][]["})()

    class _Client:
        models = _MalformedResponseExtractor._Models() if False else None  # filled below

    def __init__(self):
        models = self._Models()
        client = type("C", (), {"models": models})()
        self._inner = GeminiFormExtractor(client=client, fast_model="test")

    def extract(self, **kwargs) -> ExtractionResult:
        return self._inner.extract(**kwargs)

    def escalate_uncertain(self, **kwargs) -> ExtractionResult:
        return self._inner.escalate_uncertain(**kwargs)


# ---------------------------------------------------------------------------
# Fixture: authenticated API client with injectable service
# ---------------------------------------------------------------------------

@pytest.fixture()
def fail_client(db_setup, app, monkeypatch, tmp_path):
    """Test client with ENABLE_AI_FORM_ASSIST=1 and a monkeypatch slot for the service."""
    monkeypatch.setenv("ENABLE_AI_FORM_ASSIST", "1")
    monkeypatch.setenv("AUTH_DEFAULT_DENY_ENABLED", "0")

    with app.app_context():
        from database import db

        u = User(username="failtest", email="failtest@t.com", role="agent", is_active=True)
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()

    client = app.test_client()
    client.post(
        "/auth/login",
        data={"username": "failtest", "password": "password123"},
        follow_redirects=False,
    )
    return client, app, monkeypatch, tmp_path


def _patch_svc(monkeypatch, extractor, tmp_path):
    """Inject a service with the given extractor into both service module and view."""
    store = PrivateAuditStorage(root=tmp_path / "audit_fail")
    svc = AIFormAssistService(extractor=extractor, storage=store)
    import services.ai_form_assist.service as svc_mod

    monkeypatch.setattr(svc_mod, "ai_form_assist_service", svc)
    return svc


# ---------------------------------------------------------------------------
# 1. Provider exception → bounded HTTP response (no traceback, no raw exc text)
# ---------------------------------------------------------------------------

def test_provider_exception_response_is_bounded(fail_client):
    client, app, monkeypatch, tmp_path = fail_client
    _patch_svc(monkeypatch, _BrokenExtractor(), tmp_path)

    r = client.post(
        "/api/ai-form-assist/extractions",
        data={"form": "property", "text": "villa near downtown"},
    )

    # Must be a JSON error response — view's except Exception handler
    assert r.content_type.startswith("application/json"), (
        f"Expected JSON, got: {r.content_type}"
    )
    body_text = r.get_data(as_text=True)

    # No raw Python traceback
    assert "Traceback" not in body_text, "Response leaked a Python traceback"
    assert "traceback" not in body_text.lower()

    # Must not contain the raw exception message string
    assert "SHOULD NOT APPEAR" not in body_text, (
        "Response leaked raw exception message text"
    )
    assert "provider blew up" not in body_text, (
        "Response leaked raw exception message"
    )

    # Safe bounded error payload
    body = r.get_json()
    assert body is not None
    assert "error" in body
    # status must be an HTTP error code
    assert r.status_code in (400, 500), f"Unexpected status: {r.status_code}"


# ---------------------------------------------------------------------------
# 2. Provider exception → no CRM entity created
# ---------------------------------------------------------------------------

def test_provider_exception_does_not_create_crm_entity(fail_client):
    client, app, monkeypatch, tmp_path = fail_client
    _patch_svc(monkeypatch, _BrokenExtractor(), tmp_path)

    with app.app_context():
        before_p = Property.query.count()
        before_c = Customer.query.count()

    client.post(
        "/api/ai-form-assist/extractions",
        data={"form": "property", "text": "villa near downtown"},
    )

    with app.app_context():
        assert Property.query.count() == before_p, "Provider exception created a Property"
        assert Customer.query.count() == before_c, "Provider exception created a Customer"


# ---------------------------------------------------------------------------
# 3. Degraded/timeout extraction → bounded 201, crm_written=False, no CRM entity
# ---------------------------------------------------------------------------

def test_degraded_extraction_is_bounded(fail_client):
    client, app, monkeypatch, tmp_path = fail_client
    _patch_svc(monkeypatch, _DegradedExtractor("timeout"), tmp_path)

    with app.app_context():
        before_p = Property.query.count()

    r = client.post(
        "/api/ai-form-assist/extractions",
        data={"form": "property", "text": "villa near downtown"},
    )

    # Degraded path: extractor returns gracefully → service commits audit record
    # and returns extraction dict → view returns 201
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert body is not None

    # Contract: crm_written must be explicitly False
    assert body.get("crm_written") is False

    # Status reflects failure
    assert body.get("status") == "failed"

    # error_code must be safe/bounded (no raw exception class name leaking)
    error_code = body.get("error_code") or ""
    assert len(error_code) <= 40
    assert "Traceback" not in error_code
    assert "RuntimeError" not in error_code

    with app.app_context():
        assert Property.query.count() == before_p, "Degraded extraction created a Property"


# ---------------------------------------------------------------------------
# 4. Malformed provider response → degraded result, no CRM entity
# ---------------------------------------------------------------------------

def test_malformed_provider_response_is_bounded(fail_client):
    client, app, monkeypatch, tmp_path = fail_client
    _patch_svc(monkeypatch, _MalformedResponseExtractor(), tmp_path)

    with app.app_context():
        before_p = Property.query.count()

    r = client.post(
        "/api/ai-form-assist/extractions",
        data={"form": "property", "text": "villa near downtown"},
    )

    assert r.status_code in (201, 400, 500)
    body_text = r.get_data(as_text=True)
    assert "Traceback" not in body_text
    assert len(body_text) < 4096, "Response body is suspiciously large (possible traceback)"

    with app.app_context():
        assert Property.query.count() == before_p


# ---------------------------------------------------------------------------
# 5. Manual Property save succeeds after a failed AI extraction (cross-request isolation)
# ---------------------------------------------------------------------------

def test_manual_property_save_succeeds_after_ai_failure(fail_client, app, monkeypatch, tmp_path):
    client, app, monkeypatch, tmp_path = fail_client
    _patch_svc(monkeypatch, _BrokenExtractor(), tmp_path)

    # Request 1: AI extraction fails
    r1 = client.post(
        "/api/ai-form-assist/extractions",
        data={"form": "property", "text": "villa near downtown"},
    )
    assert r1.status_code in (400, 500), (
        f"Expected AI failure but got {r1.status_code}: {r1.get_data(as_text=True)}"
    )

    with app.app_context():
        before_p = Property.query.count()

    # Request 2: ordinary manual Property POST must still succeed
    # These are the minimum required fields for PropertyForm validation
    r2 = client.post(
        "/properties/add",
        data={
            "title": "Test Villa After Failure",
            "address": "123 Test Street",
            "sale_price": "500000",
            "property_type": "apartment",
            "bedrooms": "2",
            "bathrooms": "1",
            "square_feet": "80",
            "description": "Test property after AI failure",
            "status": "active",
            "listing_type": "sale",
            "property_category": "residential",
            "property_condition": "good",
            "floors": "1",
            "units": "1",
            "parking_spaces": "0",
            "source": "manual",
        },
        follow_redirects=False,
    )

    # Successful add redirects to the properties list
    assert r2.status_code in (200, 302), (
        f"Manual property save failed after AI failure: {r2.status_code}\n{r2.get_data(as_text=True)[:500]}"
    )

    with app.app_context():
        after_p = Property.query.count()
        # The property should have been created with user-supplied values intact
        assert after_p == before_p + 1, (
            f"Expected one new property, got {after_p - before_p}"
        )
        created = Property.query.order_by(Property.id.desc()).first()
        assert created is not None
        assert created.title == "Test Villa After Failure", (
            f"User-supplied title not preserved: {created.title!r}"
        )

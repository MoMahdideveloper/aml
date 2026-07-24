from datetime import datetime

from sqlalchemy_models import SmsOutboundMessage
from services.sms.providers.base import SMSProviderTemporaryError
from services.sms_service import sms_service


def test_sms_config_missing_marks_message_failed(app, db_setup, monkeypatch):
    monkeypatch.delenv("MELIPAYAMAK_USERNAME", raising=False)
    monkeypatch.delenv("MELIPAYAMAK_PASSWORD", raising=False)
    monkeypatch.delenv("MELIPAYAMAK_LINE_NUMBER", raising=False)
    monkeypatch.setenv("SMS_PROVIDER", "melipayamak")

    with app.app_context():
        queued = sms_service.queue_messages(["09121234567"], "hello")
        assert len(queued) == 1

        result = sms_service.process_queue(batch_size=10)
        assert result["processed"] == 1
        assert result["failed"] == 1

        msg = SmsOutboundMessage.query.get(queued[0].id)
        assert msg is not None
        assert msg.status == "failed"
        assert "Missing SMS config" in (msg.error_message or "")


def test_sms_happy_path_marks_message_sent(app, db_setup, monkeypatch):
    class _Provider:
        def send_message(self, recipient: str, message: str):
            return {"provider_message_id": "mp-12345"}

    monkeypatch.setattr(sms_service, "_get_provider", lambda provider_name: _Provider())

    with app.app_context():
        queued = sms_service.queue_messages(["09121234567"], "hello")
        result = sms_service.process_queue(batch_size=10)

        assert result["processed"] == 1
        assert result["sent"] == 1

        msg = SmsOutboundMessage.query.get(queued[0].id)
        assert msg is not None
        assert msg.status == "sent"
        assert msg.provider_message_id == "mp-12345"
        assert isinstance(msg.sent_at, datetime)


def test_sms_temporary_failure_retries_then_fails(app, db_setup, monkeypatch):
    class _FlakyProvider:
        def send_message(self, recipient: str, message: str):
            raise SMSProviderTemporaryError("Temporary provider outage")

    monkeypatch.setattr(sms_service, "_get_provider", lambda provider_name: _FlakyProvider())

    with app.app_context():
        queued = sms_service.queue_messages(["09121234567"], "hello", max_attempts=2)
        msg_id = queued[0].id

        first = sms_service.process_queue(batch_size=10)
        assert first["processed"] == 1
        assert first["retried"] == 1
        assert first["failed"] == 0

        msg_after_first = SmsOutboundMessage.query.get(msg_id)
        assert msg_after_first is not None
        assert msg_after_first.status == "pending"
        assert msg_after_first.attempts == 1

        second = sms_service.process_queue(batch_size=10)
        assert second["processed"] == 1
        assert second["failed"] == 1

        msg_after_second = SmsOutboundMessage.query.get(msg_id)
        assert msg_after_second is not None
        assert msg_after_second.status == "failed"
        assert msg_after_second.attempts == 2


def test_sms_form_send_queues_deduplicated_recipients_and_records_history(client, app, db_setup):
    """Live form contract: POST /sms/send queues + processes, then history is service-backed."""
    response = client.post(
        "/sms/send",
        data={
            "message": "api contract test",
            "segment": "all",
            "manual_phones": "09121234567,09121234567",
            "provider": "log",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/sms-broadcast")

    with app.app_context():
        history = sms_service.get_history(limit=10)
        assert len(history) == 1  # recipients are deduplicated
        assert history[0].recipient == "09121234567"
        assert history[0].status == "sent"
        assert history[0].message == "api contract test"


def test_opportunity_sms_api_contract(client, app, db_setup):
    """Live JSON contract used by opportunity workflows."""
    from services.database_service import database_service

    with app.app_context():
        customer = database_service.add_customer(
            name="SMS Opportunity Client",
            email="sms.opportunity@example.com",
            phone="09129876543",
        )
        customer_id = customer.id

    response = client.post(
        "/api/opportunities/send-sms",
        json={
            "customer_id": customer_id,
            "message": "opportunity sms contract",
            "provider": "log",
            "also_log_thread": False,
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["queued"] == 1
    assert payload["stats"]["sent"] == 1
    assert payload["phone"] == "09129876543"

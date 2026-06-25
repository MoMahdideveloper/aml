import json
from unittest.mock import patch


def test_scheduler_disabled_in_web_process_by_default(monkeypatch):
    monkeypatch.setenv("ENABLE_SCHEDULER", "0")

    from app import create_app

    app = create_app()
    assert app.config.get("SCHEDULER_ENABLED") is False


def test_automations_api_requires_admin_auth(client):
    response = client.get("/api/automations/rules")
    assert response.status_code == 401


def test_automations_api_create_and_list_rule(client, db_setup):
    with client.session_transaction() as session:
        session["admin_authenticated"] = True
        session["admin_user"] = "test_admin"

    create_response = client.post(
        "/api/automations/rules",
        data=json.dumps(
            {
                "name": "Deal Stage Follow-up",
                "trigger_type": "deal_stage_changed",
                "enabled": True,
                "conditions": {"new_status": "qualified"},
                "actions": [
                    {
                        "type": "create_task",
                        "title": "Follow up with qualified lead",
                        "priority": "high",
                    }
                ],
            }
        ),
        content_type="application/json",
    )
    assert create_response.status_code == 201
    payload = create_response.get_json()
    assert payload["rule"]["name"] == "Deal Stage Follow-up"

    list_response = client.get("/api/automations/rules")
    assert list_response.status_code == 200
    listed = list_response.get_json()
    assert listed["count"] >= 1
    assert any(rule["name"] == "Deal Stage Follow-up" for rule in listed["rules"])


def test_sms_queue_scheduler_job_executes(app, monkeypatch):
    monkeypatch.setenv("SMS_QUEUE_BATCH_SIZE", "5")

    with app.app_context():
        from services.scheduler_service import process_sms_queue_job

        with patch("services.sms_service.sms_service.process_queue") as mocked_process:
            mocked_process.return_value = {"processed": 0, "sent": 0, "failed": 0, "retried": 0}
            process_sms_queue_job()
            mocked_process.assert_called_once_with(batch_size=5)

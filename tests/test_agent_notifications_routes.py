"""Integration tests for agent notification routes and read-state updates."""

from database import db
from services.database_service import database_service
from sqlalchemy_models import AgentNotification


def _seed_agent_with_notifications():
    agent = database_service.add_agent(
        name="Notification Agent",
        email="notifications.agent@example.com",
        phone="555-888-9999",
    )

    unread_notification = AgentNotification(
        agent_id=agent.id,
        title="Unread Match",
        message="A new customer match is available.",
        notification_type="system",
        priority="high",
        status="unread",
    )
    read_notification = AgentNotification(
        agent_id=agent.id,
        title="Already Read",
        message="This notification has already been read.",
        notification_type="system",
        priority="normal",
        status="read",
    )

    db.session.add_all([unread_notification, read_notification])
    db.session.commit()
    return {
        "agent_id": agent.id,
        "unread_notification_id": unread_notification.id,
        "read_notification_id": read_notification.id,
    }


def test_get_agent_notifications_filters_unread(client, app, db_setup):
    with app.app_context():
        seeded = _seed_agent_with_notifications()

    response = client.get(f"/agents/{seeded['agent_id']}/notifications?status=unread&limit=20")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["count"] == 1
    assert payload["notifications"][0]["id"] == seeded["unread_notification_id"]
    assert payload["notifications"][0]["status"] == "unread"


def test_mark_notification_read_updates_status_and_summary(client, app, db_setup):
    with app.app_context():
        seeded = _seed_agent_with_notifications()

    summary_before = client.get(f"/api/agents/{seeded['agent_id']}/notifications/summary").get_json()
    assert summary_before["unread_count"] == 1

    mark_response = client.post(
        f"/agents/{seeded['agent_id']}/notifications/{seeded['unread_notification_id']}/read"
    )
    assert mark_response.status_code == 200
    assert mark_response.get_json()["success"] is True

    with app.app_context():
        updated = db.session.get(AgentNotification, seeded["unread_notification_id"])
        assert updated is not None
        assert updated.status == "read"
        assert updated.read_at is not None

    summary_after = client.get(f"/api/agents/{seeded['agent_id']}/notifications/summary").get_json()
    assert summary_after["unread_count"] == 0


def test_dismiss_notification_updates_status(client, app, db_setup):
    with app.app_context():
        seeded = _seed_agent_with_notifications()

    response = client.post(
        f"/agents/{seeded['agent_id']}/notifications/{seeded['unread_notification_id']}/dismiss"
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    with app.app_context():
        updated = db.session.get(AgentNotification, seeded["unread_notification_id"])
        assert updated is not None
        assert updated.status == "dismissed"


def test_mark_notification_read_not_found_returns_404(client, app, db_setup):
    with app.app_context():
        agent = database_service.add_agent(
            name="No Notification Agent",
            email="none@example.com",
            phone="555-111-2222",
        )
        agent_id = agent.id

    response = client.post(f"/agents/{agent_id}/notifications/99999/read")
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False

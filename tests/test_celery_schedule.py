from unittest.mock import patch


def test_beat_schedule_contains_required_jobs():
    from celery_app import get_celery_beat_schedule

    schedule = get_celery_beat_schedule()
    expected = {
        "process-rematch-queue",
        "run-property-matching",
        "cleanup-old-matches",
        "notification-digest",
        "process-overdue-tasks",
        "process-sms-queue",
    }
    assert expected.issubset(set(schedule.keys()))


def test_web_app_does_not_boot_scheduler():
    from app import create_app

    app = create_app()
    assert app.config.get("SCHEDULER_ENABLED") is False


def test_celery_task_dispatch_in_eager_mode(app):
    from celery_app import celery_app
    from services.celery_tasks import process_sms_queue_task

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

    with app.app_context():
        with patch("services.sms_service.sms_service.process_queue") as mocked_process:
            mocked_process.return_value = {"processed": 0, "sent": 0, "failed": 0, "retried": 0}
            result = process_sms_queue_task.delay()
            assert result.successful()
            mocked_process.assert_called_once()


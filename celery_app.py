import os

from celery import Celery
from celery.schedules import crontab

from app import create_app


def _redis_url() -> str:
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def get_celery_beat_schedule() -> dict:
    return {
        "process-rematch-queue": {
            "task": "crm.process_rematch_queue",
            "schedule": int(os.environ.get("REMATCH_QUEUE_INTERVAL_MINUTES", "2")) * 60,
        },
        "run-property-matching": {
            "task": "crm.run_property_matching",
            "schedule": int(os.environ.get("MATCHING_INTERVAL_MINUTES", "30")) * 60,
        },
        "cleanup-old-matches": {
            "task": "crm.cleanup_old_matches",
            "schedule": crontab(hour=2, minute=0),
        },
        "notification-digest": {
            "task": "crm.send_notification_digest",
            "schedule": crontab(hour=9, minute=0),
        },
        "process-overdue-tasks": {
            "task": "crm.process_overdue_tasks",
            "schedule": int(os.environ.get("OVERDUE_TASK_INTERVAL_MINUTES", "30")) * 60,
        },
        "process-sms-queue": {
            "task": "crm.process_sms_queue",
            "schedule": int(os.environ.get("SMS_QUEUE_INTERVAL_SECONDS", "30")),
        },
        "run-nightly-scoring": {
            "task": "crm.run_nightly_scoring",
            "schedule": crontab(
                hour=int(os.environ.get("SCORING_CRON_HOUR_UTC", "0")),
                minute=int(os.environ.get("SCORING_CRON_MINUTE_UTC", "0")),
            ),
        },
    }


flask_app = create_app()
celery_app = Celery(flask_app.import_name)
celery_app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL", _redis_url()),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND", _redis_url()),
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule=get_celery_beat_schedule(),
)


class FlaskContextTask(celery_app.Task):
    def __call__(self, *args, **kwargs):
        with flask_app.app_context():
            return self.run(*args, **kwargs)


celery_app.Task = FlaskContextTask


# Ensure task registration on worker boot.
import services.celery_tasks  # noqa: E402,F401

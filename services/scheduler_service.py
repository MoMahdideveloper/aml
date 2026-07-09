import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from flask import Flask, current_app

from background_matcher import background_matcher
from database import db
from sqlalchemy_models import RematchQueue
from utils.execution_tracer import log_execution


class SchedulerService:
    """
    Deprecated APScheduler facade kept for backward compatibility.
    Scheduling and queue execution are handled by Celery workers/beat.
    """

    def __init__(self, app: Optional[Flask] = None):
        self.logger = logging.getLogger(__name__)
        self.app = app
        self._initialized = False

        if app:
            self.init_app(app)

    @log_execution
    def init_app(self, app: Flask):
        if self._initialized:
            return

        self.app = app
        app.extensions["scheduler"] = self
        self._initialized = True
        self.logger.info("Scheduler compatibility service initialized (Celery mode)")

    @log_execution
    def start(self):
        self.logger.info("Scheduler start skipped: Celery Beat owns scheduling in this build")

    @log_execution
    def stop(self):
        self.logger.info("Scheduler stop noop in Celery mode")

    @log_execution
    def trigger_immediate_matching(self, property_ids=None, customer_ids=None) -> str:
        from services.celery_tasks import run_immediate_matching_task

        job_id = f"immediate_matching_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        try:
            run_immediate_matching_task.apply_async(args=[property_ids, customer_ids], task_id=job_id)
        except Exception as exc:
            self.logger.warning("Failed to enqueue immediate matching task %s: %s", job_id, exc)
        return job_id

    @log_execution
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        from celery_app import celery_app

        try:
            result = celery_app.AsyncResult(job_id)
            return {
                "id": job_id,
                "name": job_id,
                "next_run_time": None,
                "trigger": "celery",
                "state": result.state,
            }
        except Exception as exc:
            self.logger.error("Error getting Celery task status for %s: %s", job_id, exc)
            return None

    @log_execution
    def list_active_jobs(self) -> List[Dict]:
        from celery_app import get_celery_beat_schedule

        jobs = []
        for job_id, payload in get_celery_beat_schedule().items():
            jobs.append(
                {
                    "id": job_id,
                    "name": payload.get("task", ""),
                    "next_run_time": None,
                    "trigger": str(payload.get("schedule")),
                }
            )
        return jobs


@log_execution
def run_property_matching_job():
    from services.monitoring_service import monitoring_service

    job_id = "scheduled_property_matching"
    session_id = None
    logger = logging.getLogger(__name__)

    try:
        with current_app.app_context():
            session_id = monitoring_service.log_matching_job_start(job_id, "scheduled")
            result = background_matcher.run_matching_cycle(trigger_source="scheduled")
            logger.info("Property matching job completed: %s", result)
    except Exception as exc:
        logger.error("Error in property matching job: %s", exc)
        if session_id:
            monitoring_service.log_matching_error(session_id, exc, {"job_type": "scheduled"})


@log_execution
def process_rematch_queue_job():
    """
    Drain RematchQueue quickly for always-on matching.

    Property and customer items are matched in *separate* cycles so a batch that
    mixes both types does not incorrectly narrow to only those IDs crossed
    against each other.
    """
    logger = logging.getLogger(__name__)

    try:
        with current_app.app_context():
            batch_size = int(current_app.config.get("REMATCH_QUEUE_BATCH_SIZE") or 50)
            batch_size = int(os.environ.get("REMATCH_QUEUE_BATCH_SIZE", str(batch_size)))
            max_retries = int(os.environ.get("REMATCH_QUEUE_MAX_RETRIES", "5"))
            stale_minutes = int(os.environ.get("REMATCH_STALE_PROCESSING_MINUTES", "15"))

            # Re-queue items stuck in processing (worker crash / timeout)
            stale_before = datetime.utcnow() - timedelta(minutes=stale_minutes)
            stuck = (
                RematchQueue.query.filter(
                    RematchQueue.status == "processing",
                    RematchQueue.updated_at < stale_before,
                )
                .limit(batch_size)
                .all()
            )
            for item in stuck:
                item.status = "pending"
                item.retries = (item.retries or 0) + 1
                item.last_error = "requeued_stale_processing"
                item.updated_at = datetime.utcnow()
            if stuck:
                db.session.commit()
                logger.warning("Requeued %s stale rematch items", len(stuck))

            pending = (
                RematchQueue.query.filter_by(status="pending")
                .order_by(RematchQueue.created_at.asc())
                .limit(batch_size)
                .all()
            )
            if not pending:
                return

            property_items = [q for q in pending if q.entity_type == "property"]
            customer_items = [q for q in pending if q.entity_type == "customer"]
            property_ids = sorted({q.entity_id for q in property_items})
            customer_ids = sorted({q.entity_id for q in customer_items})

            for item in pending:
                item.status = "processing"
                item.updated_at = datetime.utcnow()
            db.session.commit()

            results = []
            # Separate cycles: each entity type vs full complementary set
            if property_ids:
                results.append(
                    background_matcher.run_matching_cycle(
                        property_ids=property_ids,
                        customer_ids=None,
                        trigger_source="queue_property",
                    )
                )
            if customer_ids:
                results.append(
                    background_matcher.run_matching_cycle(
                        property_ids=None,
                        customer_ids=customer_ids,
                        trigger_source="queue_customer",
                    )
                )
            if not results:
                results.append({"status": "completed", "matches_found": 0})

            # Success if every cycle completed or was intentionally skipped (dedupe)
            ok_statuses = {"completed", "skipped"}
            all_ok = all(r.get("status") in ok_statuses for r in results)
            err = "; ".join(
                str(r.get("error") or r.get("status"))
                for r in results
                if r.get("status") not in ok_statuses
            ) or "unknown"

            if all_ok:
                for item in pending:
                    item.status = "done"
                    item.updated_at = datetime.utcnow()
            else:
                for item in pending:
                    item.retries = (item.retries or 0) + 1
                    item.last_error = str(err)[:500]
                    item.updated_at = datetime.utcnow()
                    # Retry later until max; then leave as failed
                    if item.retries < max_retries:
                        item.status = "pending"
                    else:
                        item.status = "failed"

            db.session.commit()
            total_matches = sum(int(r.get("matches_saved") or 0) for r in results)
            total_notes = sum(int(r.get("notifications_created") or 0) for r in results)
            logger.info(
                "Rematch queue processed: %s items, properties=%s, customers=%s, "
                "matches_saved=%s, notifications=%s, ok=%s",
                len(pending),
                len(property_ids),
                len(customer_ids),
                total_matches,
                total_notes,
                all_ok,
            )
    except Exception as exc:
        db.session.rollback()
        logger.error("Error processing rematch queue: %s", exc)


@log_execution
def cleanup_old_matches_job():
    from sqlalchemy_models import AgentNotification, PropertyMatch

    logger = logging.getLogger(__name__)

    try:
        with current_app.app_context():
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            old_matches = db.session.query(PropertyMatch).filter(
                PropertyMatch.created_at < cutoff_date,
                PropertyMatch.status.in_(["dismissed", "reviewed"]),
            ).all()

            for match in old_matches:
                db.session.query(AgentNotification).filter_by(property_match_id=match.id).delete()
                db.session.delete(match)

            queue_cutoff = datetime.utcnow() - timedelta(days=7)
            db.session.query(RematchQueue).filter(
                RematchQueue.updated_at < queue_cutoff,
                RematchQueue.status.in_(["done", "failed"]),
            ).delete(synchronize_session=False)

            notification_cutoff = datetime.utcnow() - timedelta(days=60)
            old_notifications = db.session.query(AgentNotification).filter(
                AgentNotification.created_at < notification_cutoff,
                AgentNotification.status.in_(["read", "dismissed"]),
            )
            old_notifications.delete(synchronize_session=False)
            db.session.commit()

            logger.info("Cleanup completed")
    except Exception as exc:
        db.session.rollback()
        logger.error("Error in cleanup job: %s", exc)


@log_execution
def send_notification_digest_job():
    from sqlalchemy_models import Agent, AgentNotification

    logger = logging.getLogger(__name__)

    try:
        with current_app.app_context():
            agents_with_notifications = (
                db.session.query(Agent)
                .join(AgentNotification, Agent.id == AgentNotification.agent_id)
                .filter(
                    AgentNotification.status == "unread",
                    AgentNotification.created_at >= datetime.utcnow() - timedelta(days=1),
                )
                .distinct()
                .all()
            )

            for agent in agents_with_notifications:
                unread_count = (
                    db.session.query(AgentNotification)
                    .filter_by(agent_id=agent.id, status="unread")
                    .filter(AgentNotification.created_at >= datetime.utcnow() - timedelta(days=1))
                    .count()
                )
                logger.info("Daily digest: %s has %s unread notifications", agent.email, unread_count)
    except Exception as exc:
        logger.error("Error in notification digest job: %s", exc)


@log_execution
def process_overdue_tasks_job():
    logger = logging.getLogger(__name__)

    try:
        with current_app.app_context():
            from services.automation_service import automation_service

            processed = automation_service.process_overdue_tasks()
            logger.info("Overdue task automation processed: %s", processed)
    except Exception as exc:
        logger.error("Error processing overdue tasks: %s", exc)


@log_execution
def process_sms_queue_job():
    from services.sms_service import sms_service

    logger = logging.getLogger(__name__)

    try:
        with current_app.app_context():
            batch_size = int(current_app.config.get("SMS_QUEUE_BATCH_SIZE") or 20)
            batch_size = int(os.environ.get("SMS_QUEUE_BATCH_SIZE", str(batch_size)))
            result = sms_service.process_queue(batch_size=batch_size)
            if result.get("processed", 0) > 0:
                logger.info(
                    "SMS queue processed: processed=%s sent=%s failed=%s retried=%s",
                    result.get("processed", 0),
                    result.get("sent", 0),
                    result.get("failed", 0),
                    result.get("retried", 0),
                )
    except Exception as exc:
        logger.error("Error processing SMS queue: %s", exc)


@log_execution
def run_immediate_matching_job(property_ids=None, customer_ids=None):
    logger = logging.getLogger(__name__)

    try:
        with current_app.app_context():
            results = []
            # Same rule as queue: do not AND both ID lists into one narrow cross product
            if property_ids and customer_ids:
                results.append(
                    background_matcher.run_matching_cycle(
                        property_ids=property_ids,
                        customer_ids=None,
                        trigger_source="manual_property",
                    )
                )
                results.append(
                    background_matcher.run_matching_cycle(
                        property_ids=None,
                        customer_ids=customer_ids,
                        trigger_source="manual_customer",
                    )
                )
            else:
                results.append(
                    background_matcher.run_matching_cycle(
                        property_ids=property_ids,
                        customer_ids=customer_ids,
                        trigger_source="manual",
                    )
                )
            logger.info("Immediate matching job completed: %s", results)
    except Exception as exc:
        logger.error("Error in immediate matching job: %s", exc)


scheduler_service = SchedulerService()

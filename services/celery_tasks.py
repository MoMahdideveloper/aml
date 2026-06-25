import logging
from typing import Optional, Dict, Any

from celery_app import celery_app
from database import db
from sqlalchemy_models import Property, PropertyEmbedding
from utils.execution_tracer import log_execution


logger = logging.getLogger(__name__)


@celery_app.task(name="crm.process_rematch_queue")
@log_execution
def process_rematch_queue_task() -> Dict[str, Any]:
    """Process rematch queue job."""
    try:
        from services.scheduler_service import process_rematch_queue_job

        process_rematch_queue_job()
        logger.info(
            "Rematch queue processed successfully",
            extra={
                "task": "process_rematch_queue",
                "status": "success"
            }
        )
        return {"status": "ok"}
    except Exception as exc:
        logger.error(
            "Failed to process rematch queue",
            extra={
                "task": "process_rematch_queue",
                "status": "error",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
        )
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="crm.run_property_matching")
@log_execution
def run_property_matching_task() -> Dict[str, Any]:
    """Run property matching job."""
    try:
        from services.scheduler_service import run_property_matching_job

        run_property_matching_job()
        logger.info(
            "Property matching completed successfully",
            extra={
                "task": "run_property_matching",
                "status": "success"
            }
        )
        return {"status": "ok"}
    except Exception as exc:
        logger.error(
            "Failed to run property matching",
            extra={
                "task": "run_property_matching",
                "status": "error",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
        )
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="crm.cleanup_old_matches")
@log_execution
def cleanup_old_matches_task() -> Dict[str, Any]:
    """Cleanup old matches job."""
    try:
        from services.scheduler_service import cleanup_old_matches_job

        cleanup_old_matches_job()
        logger.info(
            "Old matches cleanup completed successfully",
            extra={
                "task": "cleanup_old_matches",
                "status": "success"
            }
        )
        return {"status": "ok"}
    except Exception as exc:
        logger.error(
            "Failed to cleanup old matches",
            extra={
                "task": "cleanup_old_matches",
                "status": "error",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
        )
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="crm.send_notification_digest")
@log_execution
def send_notification_digest_task() -> Dict[str, Any]:
    """Send notification digest job."""
    try:
        from services.scheduler_service import send_notification_digest_job

        send_notification_digest_job()
        logger.info(
            "Notification digest sent successfully",
            extra={
                "task": "send_notification_digest",
                "status": "success"
            }
        )
        return {"status": "ok"}
    except Exception as exc:
        logger.error(
            "Failed to send notification digest",
            extra={
                "task": "send_notification_digest",
                "status": "error",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
        )
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="crm.process_overdue_tasks")
@log_execution
def process_overdue_tasks_task() -> Dict[str, Any]:
    """Process overdue tasks job."""
    try:
        from services.scheduler_service import process_overdue_tasks_job

        process_overdue_tasks_job()
        logger.info(
            "Overdue tasks processed successfully",
            extra={
                "task": "process_overdue_tasks",
                "status": "success"
            }
        )
        return {"status": "ok"}
    except Exception as exc:
        logger.error(
            "Failed to process overdue tasks",
            extra={
                "task": "process_overdue_tasks",
                "status": "error",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
        )
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="crm.process_sms_queue")
@log_execution
def process_sms_queue_task() -> Dict[str, Any]:
    """Process SMS queue job."""
    try:
        from services.scheduler_service import process_sms_queue_job

        process_sms_queue_job()
        logger.info(
            "SMS queue processed successfully",
            extra={
                "task": "process_sms_queue",
                "status": "success"
            }
        )
        return {"status": "ok"}
    except Exception as exc:
        logger.error(
            "Failed to process SMS queue",
            extra={
                "task": "process_sms_queue",
                "status": "error",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
        )
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="crm.run_nightly_scoring")
@log_execution
def run_nightly_scoring_task() -> Dict[str, Any]:
    """Run nightly scoring job."""
    try:
        from tasks.scoring_engine import run_nightly_scoring_job

        result = run_nightly_scoring_job()
        logger.info(
            "Nightly scoring completed successfully",
            extra={
                "task": "run_nightly_scoring",
                "status": "success",
                "result": result
            }
        )
        return {"status": "ok", "result": result}
    except Exception as exc:
        logger.error(
            "Failed to run nightly scoring",
            extra={
                "task": "run_nightly_scoring",
                "status": "error",
                "error": str(exc),
                "error_type": type(exc).__name__
            }
        )
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="crm.run_immediate_matching")
@log_execution
def run_immediate_matching_task(
    property_ids: Optional[list[int]] = None,
    customer_ids: Optional[list[int]] = None,
) -> Dict[str, Any]:
    """Run immediate matching job."""
    try:
        from services.scheduler_service import run_immediate_matching_job

        run_immediate_matching_job(property_ids=property_ids, customer_ids=customer_ids)
        logger.info(
            "Immediate matching completed successfully",
            extra={
                "task": "run_immediate_matching",
                "status": "success",
                "property_count": len(property_ids) if property_ids else 0,
                "customer_count": len(customer_ids) if customer_ids else 0
            }
        )
        return {"status": "ok"}
    except Exception as exc:
        logger.error(
            "Failed to run immediate matching",
            extra={
                "task": "run_immediate_matching",
                "status": "error",
                "error": str(exc),
                "error_type": type(exc).__name__,
                "property_count": len(property_ids) if property_ids else 0,
                "customer_count": len(customer_ids) if customer_ids else 0
            }
        )
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="crm.sync_property_embedding")
@log_execution
def sync_property_embedding_task(property_id: int, action: str = "upsert") -> Dict[str, Any]:
    """Sync property embedding job."""
    try:
        from services.vector_service import vector_service

        property_obj = db.session.get(Property, property_id)

        if action == "delete" or not property_obj or property_obj.is_deleted or property_obj.status != "active":
            embedding = PropertyEmbedding.query.filter_by(property_id=property_id).first()
            if embedding:
                db.session.delete(embedding)
                db.session.commit()
                logger.info(
                    "Property embedding deleted successfully",
                    extra={
                        "task": "sync_property_embedding",
                        "status": "success",
                        "action": "delete",
                        "property_id": property_id
                    }
                )
                return {"status": "deleted", "property_id": property_id}
            else:
                logger.info(
                    "No embedding found to delete",
                    extra={
                        "task": "sync_property_embedding",
                        "status": "success",
                        "action": "delete",
                        "property_id": property_id,
                        "reason": "no_embedding_found"
                    }
                )
                return {"status": "deleted", "property_id": property_id}

        ok = vector_service.index_properties([property_obj])
        if not ok:
            logger.warning(
                "Failed embedding sync for property",
                extra={
                    "task": "sync_property_embedding",
                    "status": "warning",
                    "action": action,
                    "property_id": property_id
                }
            )
            return {"status": "failed", "property_id": property_id}
        else:
            logger.info(
                "Property embedding synced successfully",
                extra={
                    "task": "sync_property_embedding",
                    "status": "success",
                    "action": "upsert",
                    "property_id": property_id
                }
            )
            return {"status": "upserted", "property_id": property_id}

    except Exception as exc:
        logger.error(
            "Failed to sync property embedding",
            extra={
                "task": "sync_property_embedding",
                "status": "error",
                "action": action,
                "property_id": property_id,
                "error": str(exc),
                "error_type": type(exc).__name__
            }
        )
        return {"status": "error", "message": str(exc)}


@celery_app.task(name="crm.handle_environment_variable_change")
@log_execution
def handle_environment_variable_change(entity_type: str, entity_id: int, reason: str) -> Dict[str, Any]:
    """
    Handle environment variable changes by performing any necessary background work.
    This includes logging the change and potentially sending notifications for critical changes.
    """
    try:
        # For environment variables, we use a hash of the key as entity_id
        # To do meaningful work, we would need to look up the actual variable,
        # but since this runs in a Celery worker, we don't have easy access to
        # the specific variable that changed without additional lookup mechanisms.

        # For now, we log the change. In a more sophisticated implementation,
        # we could:
        # 1. Send notifications to administrators about environment variable changes
        # 2. Clear application caches that might depend on environment variables
        # 3. Validate that critical services can still initialize with the new values

        logger.info(
            "Environment variable change processed",
            extra={
                "task": "handle_environment_variable_change",
                "status": "success",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "reason": reason
            }
        )

        # Example of what we could do in the future:
        # if reason in ["environment_variable_created", "environment_variable_updated", "environment_variable_deleted"]:
        #     # Send notification to admins about the change
        #     notification_service.notify_admins_of_env_change(entity_type, entity_id, reason)

        return {"status": "processed"}
    except Exception as exc:
        logger.error(
            "Error handling environment variable change",
            extra={
                "task": "handle_environment_variable_change",
                "status": "error",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "reason": reason,
                "error": str(exc),
                "error_type": type(exc).__name__
            }
        )
        return {"status": "error", "message": str(exc)}

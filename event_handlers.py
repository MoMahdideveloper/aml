import logging
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import event, select
from sqlalchemy.orm import Session, object_session

from database import db
from sqlalchemy_models import AgentNotification, Customer, Property, PropertyMatch, RematchQueue, EnvironmentVariable, EnvironmentChangeLog


class EventHandlers:
    """
    Database event handlers that enqueue lightweight rematch requests.
    Heavy matching work is delegated to worker scheduler jobs.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._registered = False

    def register_handlers(self):
        if self._registered:
            return

        event.listen(Property, "after_insert", self._on_property_created)
        event.listen(Property, "after_update", self._on_property_updated)
        event.listen(Property, "after_delete", self._on_property_deleted)
        event.listen(Customer, "after_insert", self._on_customer_created)
        event.listen(Customer, "after_update", self._on_customer_updated)
        event.listen(EnvironmentVariable, "after_insert", self._on_environment_variable_created)
        event.listen(EnvironmentVariable, "after_update", self._on_environment_variable_updated)
        event.listen(EnvironmentVariable, "after_delete", self._on_environment_variable_deleted)
        event.listen(Session, "after_commit", self._on_session_after_commit)
        event.listen(Session, "after_rollback", self._on_session_after_rollback)

        self._registered = True
        self.logger.info("Database event handlers registered")

    def _enqueue_rematch(self, connection, entity_type: str, entity_id: int, reason: str) -> None:
        dedupe_key = f"{entity_type}:{entity_id}"
        table = RematchQueue.__table__

        # Check if pending/processing item exists for the same dedupe key.
        existing = connection.execute(
            select(table.c.id).where(
                table.c.dedupe_key == dedupe_key,
                table.c.status.in_(["pending", "processing"]),
            )
        ).first()
        if existing:
            return

        connection.execute(
            table.insert().values(
                entity_type=entity_type,
                entity_id=entity_id,
                reason=reason,
                status="pending",
                retries=0,
                dedupe_key=dedupe_key,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )

    def _enqueue_environment_variable_task(self, connection, entity_type: str, entity_id: int, reason: str) -> None:
        """
        Queue environment variable change tasks to run after DB commit.
        Running Celery .delay() inside mapper flush events can corrupt session state,
        especially when Celery eager mode is enabled in tests.
        """
        session = connection
        try:
            pending = session.info.setdefault("pending_environment_variable_tasks", [])
            pending.append((entity_type, entity_id, reason))
        except Exception:
            # Fallback to immediate dispatch if no SQLAlchemy session is available.
            self._dispatch_environment_variable_task(entity_type, entity_id, reason)

    def _dispatch_environment_variable_task(self, entity_type: str, entity_id: int, reason: str) -> None:
        try:
            from services.celery_tasks import handle_environment_variable_change
            handle_environment_variable_change.delay(entity_type, entity_id, reason)
        except Exception as exc:
            self.logger.warning(
                "Failed to dispatch environment variable change task for %s:%s (%s): %s",
                entity_type,
                entity_id,
                reason,
                exc,
            )

    def _dispatch_vector_sync_task(self, property_id: int, action: str) -> None:
        try:
            from services.celery_tasks import sync_property_embedding_task

            sync_property_embedding_task.delay(property_id, action)
        except Exception as exc:
            self.logger.warning(
                "Failed to enqueue vector sync for property %s (%s): %s",
                property_id,
                action,
                exc,
            )

    def _enqueue_vector_sync_task(self, property_id: int, action: str, target: Optional[Property] = None) -> None:
        """
        Queue vector sync tasks to run after DB commit.
        Running Celery `.delay()` inside mapper flush events can corrupt session state,
        especially when Celery eager mode is enabled in tests.
        """
        session = object_session(target) if target is not None else db.session

        try:
            pending = session.info.setdefault("pending_vector_sync_tasks", [])
            pending.append((property_id, action))
        except Exception:
            # Fallback to immediate dispatch if no SQLAlchemy session is available.
            self._dispatch_vector_sync_task(property_id, action)

    def _dispatch_vocab_occurrence_task(self, entity_type: str, entity_id: int) -> None:
        try:
            from services.celery_tasks import reindex_vocab_occurrences_task

            reindex_vocab_occurrences_task.delay(entity_type=entity_type, entity_id=entity_id)
        except Exception as exc:
            self.logger.warning(
                "Failed to enqueue vocab occurrence reindex for %s:%s: %s",
                entity_type,
                entity_id,
                exc,
            )

    def _enqueue_vocab_occurrence_task(
        self, entity_type: str, entity_id: int, target=None
    ) -> None:
        session = object_session(target) if target is not None else db.session
        try:
            pending = session.info.setdefault("pending_vocab_occurrence_tasks", [])
            pending.append((entity_type, entity_id))
        except Exception:
            self._dispatch_vocab_occurrence_task(entity_type, entity_id)

    def _on_session_after_commit(self, session: Session) -> None:
        # Handle pending vector sync tasks
        pending_vector_sync = session.info.pop("pending_vector_sync_tasks", [])
        if pending_vector_sync:
            # Keep last action per property in the same transaction.
            last_actions: Dict[int, str] = {}
            for property_id, action in pending_vector_sync:
                last_actions[property_id] = action

            for property_id, action in last_actions.items():
                self._dispatch_vector_sync_task(property_id, action)

        # Handle pending environment variable tasks
        pending_env_tasks = session.info.pop("pending_environment_variable_tasks", [])
        if pending_env_tasks:
            # Keep last action per environment variable key in the same transaction.
            last_actions: Dict[int, str] = {}
            for entity_type, entity_id, reason in pending_env_tasks:
                # Use entity_id as the key for deduplication within the same transaction
                last_actions[entity_id] = (entity_type, reason)

            for entity_id, (entity_type, reason) in last_actions.items():
                self._dispatch_environment_variable_task(entity_type, entity_id, reason)

        pending_vocab = session.info.pop("pending_vocab_occurrence_tasks", [])
        if pending_vocab:
            seen = set()
            for entity_type, entity_id in pending_vocab:
                key = (entity_type, entity_id)
                if key in seen:
                    continue
                seen.add(key)
                self._dispatch_vocab_occurrence_task(entity_type, entity_id)

    def _on_session_after_rollback(self, session: Session) -> None:
        session.info.pop("pending_vector_sync_tasks", None)
        session.info.pop("pending_environment_variable_tasks", None)
        session.info.pop("pending_vocab_occurrence_tasks", None)


    def _on_property_created(self, mapper, connection, target: Property):
        try:
            if target.status == "active" and not target.is_deleted:
                self._enqueue_rematch(connection, "property", target.id, "property_created")
                self._enqueue_vector_sync_task(target.id, "upsert", target=target)
                self._enqueue_vocab_occurrence_task("property", target.id, target=target)
            else:
                self._enqueue_vector_sync_task(target.id, "delete", target=target)
        except Exception as exc:
            self.logger.error(f"Error handling property creation event: {exc}")


    def _on_property_updated(self, mapper, connection, target: Property):
        try:
            changes = self._get_property_changes(target)
            if not changes:
                return

            significant = {
                "price",
                "rahn",
                "ejare",
                "bedrooms",
                "bathrooms",
                "property_type",
                "status",
                "square_feet",
                "description",
                "neighborhood",
                "is_deleted",
            }
            if target.status == "active" and not target.is_deleted and significant.intersection(changes.keys()):
                self._enqueue_rematch(connection, "property", target.id, "property_updated")
                self._enqueue_vector_sync_task(target.id, "upsert", target=target)
                text_fields = {
                    "description",
                    "neighborhood",
                    "title",
                    "property_features",
                    "property_type",
                }
                if text_fields.intersection(changes.keys()):
                    self._enqueue_vocab_occurrence_task("property", target.id, target=target)
            elif {"status", "is_deleted"}.intersection(changes.keys()) or target.is_deleted or target.status != "active":
                self._enqueue_vector_sync_task(target.id, "delete", target=target)

        except Exception as exc:
            self.logger.error(f"Error handling property update event: {exc}")


    def _on_property_deleted(self, mapper, connection, target: Property):
        try:
            self._enqueue_vector_sync_task(target.id, "delete", target=target)
        except Exception as exc:
            self.logger.error(f"Error handling property delete event: {exc}")

    def _on_customer_created(self, mapper, connection, target: Customer):
        try:
            if target.status in ["prospect", "active"]:
                self._enqueue_rematch(connection, "customer", target.id, "customer_created")
        except Exception as exc:
            self.logger.error(f"Error handling customer creation event: {exc}")

    def _on_customer_updated(self, mapper, connection, target: Customer):
        try:
            changes = self._get_customer_changes(target)
            if not changes:
                return

            preference_changes = {
                "budget_min",
                "budget_max",
                "preferred_bedrooms",
                "preferred_bathrooms",
                "preferred_type",
                "location_preference",
                "status",
            }
            if target.status in ["prospect", "active"] and preference_changes.intersection(changes.keys()):
                self._enqueue_rematch(connection, "customer", target.id, "customer_updated")
        except Exception as exc:
            self.logger.error(f"Error handling customer update event: {exc}")

    def _get_property_changes(self, property_obj: Property) -> Dict[str, Any]:
        changes: Dict[str, Any] = {}
        state = property_obj.__dict__.get("_sa_instance_state")
        if state and hasattr(state, "committed_state"):
            committed = state.committed_state
            current = {key: getattr(property_obj, key) for key in committed.keys()}
            for key, old_value in committed.items():
                if old_value != current.get(key):
                    changes[key] = {"old": old_value, "new": current.get(key)}
        return changes

    def _get_customer_changes(self, customer: Customer) -> Dict[str, Any]:
        changes: Dict[str, Any] = {}
        state = customer.__dict__.get("_sa_instance_state")
        if state and hasattr(state, "committed_state"):
            committed = state.committed_state
            current = {key: getattr(customer, key) for key in committed.keys()}
            for key, old_value in committed.items():
                if old_value != current.get(key):
                    changes[key] = {"old": old_value, "new": current.get(key)}
        return changes

    def _on_environment_variable_created(self, mapper, connection, target: EnvironmentVariable):
        try:
            self._enqueue_environment_variable_task(connection, "environment", hash(target.key) % 1000000, "environment_variable_created")
            # Environment variable changes might require clearing caches or restarting services
            # We queue a task to handle any necessary background work after commit
        except Exception as exc:
            self.logger.error(f"Error handling environment variable creation event: {exc}")

    def _on_environment_variable_updated(self, mapper, connection, target: EnvironmentVariable):
        try:
            changes = self._get_environment_variable_changes(target)
            if not changes:
                return

            # Queue environment variable change task for any environment variable change
            self._enqueue_environment_variable_task(connection, "environment", hash(target.key) % 1000000, "environment_variable_updated")
            # Note: In a more sophisticated system, we might want to handle specific environment variables differently
            # For example, certain variables might require service restarts or cache clearing
        except Exception as exc:
            self.logger.error(f"Error handling environment variable update event: {exc}")

    def _on_environment_variable_deleted(self, mapper, connection, target: EnvironmentVariable):
        try:
            self._enqueue_environment_variable_task(connection, "environment", hash(target.key) % 1000000, "environment_variable_deleted")
            # Environment variable deletion might require clearing caches or restarting services
            # We queue a task to handle any necessary background work after commit
        except Exception as exc:
            self.logger.error(f"Error handling environment variable delete event: {exc}")

    def _get_environment_variable_changes(self, environment_variable: EnvironmentVariable) -> Dict[str, Any]:
        changes: Dict[str, Any] = {}
        state = environment_variable.__dict__.get("_sa_instance_state")
        if state and hasattr(state, "committed_state"):
            committed = state.committed_state
            current = {key: getattr(environment_variable, key) for key in committed.keys()}
            for key, old_value in committed.items():
                if old_value != current.get(key):
                    changes[key] = {"old": old_value, "new": current.get(key)}
        return changes

    def _on_session_after_commit(self, session: Session) -> None:
        # Handle pending vector sync tasks
        pending_vector_sync = session.info.pop("pending_vector_sync_tasks", [])
        if pending_vector_sync:
            # Keep last action per property in the same transaction.
            last_actions: Dict[int, str] = {}
            for property_id, action in pending_vector_sync:
                last_actions[property_id] = action

            for property_id, action in last_actions.items():
                self._dispatch_vector_sync_task(property_id, action)

        # Handle pending environment variable tasks
        pending_env_tasks = session.info.pop("pending_environment_variable_tasks", [])
        if pending_env_tasks:
            # Keep last action per environment variable key in the same transaction.
            last_actions: Dict[int, str] = {}
            for entity_type, entity_id, reason in pending_env_tasks:
                # Use entity_id as the key for deduplication within the same transaction
                last_actions[entity_id] = (entity_type, reason)

            for entity_id, (entity_type, reason) in last_actions.items():
                self._dispatch_environment_variable_task(entity_type, entity_id, reason)

    def _on_session_after_rollback(self, session: Session) -> None:
        session.info.pop("pending_vector_sync_tasks", None)
        session.info.pop("pending_environment_variable_tasks", None)

    def manual_trigger_matching(
        self,
        property_ids: Optional[list] = None,
        customer_ids: Optional[list] = None,
    ) -> str:
        """Manual trigger now enqueues rematch requests for worker processing."""
        with db.session.begin():
            if property_ids:
                for property_id in property_ids:
                    dedupe = f"property:{property_id}"
                    exists = RematchQueue.query.filter(
                        RematchQueue.dedupe_key == dedupe,
                        RematchQueue.status.in_(["pending", "processing"]),
                    ).first()
                    if not exists:
                        db.session.add(
                            RematchQueue(
                                entity_type="property",
                                entity_id=property_id,
                                reason="manual_trigger",
                                dedupe_key=dedupe,
                            )
                        )

            if customer_ids:
                for customer_id in customer_ids:
                    dedupe = f"customer:{customer_id}"
                    exists = RematchQueue.query.filter(
                        RematchQueue.dedupe_key == dedupe,
                        RematchQueue.status.in_(["pending", "processing"]),
                    ).first()
                    if not exists:
                        db.session.add(
                            RematchQueue(
                                entity_type="customer",
                                entity_id=customer_id,
                                reason="manual_trigger",
                                dedupe_key=dedupe,
                            )
                        )

        return f"queued_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    def get_matching_stats(self) -> Dict[str, Any]:
        try:
            since = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            recent_matches = db.session.query(PropertyMatch).filter(PropertyMatch.created_at >= since).count()
            recent_notifications = db.session.query(AgentNotification).filter(AgentNotification.created_at >= since).count()
            high_score_matches = db.session.query(PropertyMatch).filter(
                PropertyMatch.created_at >= since,
                PropertyMatch.match_score >= 0.8,
            ).count()
            pending_notifications = db.session.query(AgentNotification).filter(AgentNotification.status == "unread").count()
            queued = db.session.query(RematchQueue).filter(RematchQueue.status == "pending").count()

            return {
                "recent_matches_24h": recent_matches,
                "recent_notifications_24h": recent_notifications,
                "high_score_matches_24h": high_score_matches,
                "pending_notifications": pending_notifications,
                "queued_rematches": queued,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            self.logger.error(f"Error getting matching stats: {exc}")
            return {"error": str(exc), "timestamp": datetime.utcnow().isoformat()}


# Global instance

event_handlers = EventHandlers()

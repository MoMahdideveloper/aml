import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

from database import db
from services.gemini_service import gemini_service
from services.monitoring_service import monitoring_service
from services.vector_service import vector_service
from sqlalchemy_models import (
    AgentNotification,
    Customer,
    MatchingJobRun,
    Property,
    PropertyMatch,
)


class BackgroundMatcher:
    """Background matching engine for property-customer recommendations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Make thresholds configurable via environment variables for tuning
        # 0.40 default: without Gemini embeddings pure-rule hybrids often land 40–55%
        self.min_match_score = float(os.environ.get("MATCHER_MIN_SCORE", "0.40"))
        self.notification_threshold = float(os.environ.get("MATCHER_NOTIFICATION_THRESHOLD", "0.7"))
        self.high_priority_threshold = float(os.environ.get("MATCHER_HIGH_PRIORITY_THRESHOLD", "0.85"))
        # Notify on score rise only when improvement is meaningful (avoid spam)
        self.score_improve_delta = float(os.environ.get("MATCHER_SCORE_IMPROVE_DELTA", "0.05"))
        # Suppress duplicate unread notifications for the same match
        self.notify_dedupe = os.environ.get("MATCHER_NOTIFY_DEDUPE", "1") == "1"

    def _build_idempotency_key(
        self,
        property_ids: Optional[List[int]],
        customer_ids: Optional[List[int]],
        trigger_source: str,
    ) -> str:
        base = {
            "trigger": trigger_source,
            "properties": sorted(property_ids or []),
            "customers": sorted(customer_ids or []),
            "bucket": datetime.utcnow().strftime("%Y%m%d%H"),
        }
        return hashlib.sha256(json.dumps(base, sort_keys=True).encode("utf-8")).hexdigest()[:32]

    def _begin_matching_run(
        self,
        idempotency_key: str,
        trigger_source: str,
        property_ids: Optional[List[int]],
        customer_ids: Optional[List[int]],
    ) -> Optional[MatchingJobRun]:
        existing = MatchingJobRun.query.filter_by(idempotency_key=idempotency_key).first()
        if existing and existing.status in ["running", "completed"]:
            self.logger.info(f"Skipping duplicate matching run: {idempotency_key}")
            return None

        if existing:
            # For failed jobs, create a new attempt instead of updating the existing one
            if existing.status == "failed":
                self.logger.info(f"Previous matching job {existing.id} failed, creating new attempt")
                run = MatchingJobRun(
                    idempotency_key=idempotency_key,
                    status="running",
                    trigger_source=trigger_source,
                    property_ids=json.dumps(property_ids or []),
                    customer_ids=json.dumps(customer_ids or []),
                )
                db.session.add(run)
            else:
                # For other statuses (e.g., pending, cancelled), update the existing job
                existing.status = "running"
                existing.started_at = datetime.utcnow()
                existing.finished_at = None
                existing.trigger_source = trigger_source
                existing.property_ids = json.dumps(property_ids or [])
                existing.customer_ids = json.dumps(customer_ids or [])
                existing.result_summary = None
                run = existing
        else:
            run = MatchingJobRun(
                idempotency_key=idempotency_key,
                status="running",
                trigger_source=trigger_source,
                property_ids=json.dumps(property_ids or []),
                customer_ids=json.dumps(customer_ids or []),
            )
            db.session.add(run)

        db.session.commit()
        return run

    def find_property_matches(
        self,
        property_ids: Optional[List[int]] = None,
        customer_ids: Optional[List[int]] = None,
        batch_size: int = 50,
    ) -> List[Dict]:
        matches: List[Dict] = []

        try:
            properties = self._get_properties_for_matching(property_ids, batch_size)
            customers = self._get_customers_for_matching(customer_ids, batch_size)
            if not properties or not customers:
                self.logger.info("No properties or customers available for matching")
                return []

            for customer in customers:
                candidates = self._prefilter_candidate_properties(customer, properties)
                if not candidates:
                    continue
                # Deduplicate candidates by property id to avoid processing the same property multiple times for the same customer
                seen_property_ids = set()
                deduped_candidates = []
                for prop in candidates:
                    if prop.id not in seen_property_ids:
                        seen_property_ids.add(prop.id)
                        deduped_candidates.append(prop)
                if not deduped_candidates:
                    continue
                matches.extend(self._process_customer_candidates(customer, deduped_candidates))

            valid_matches = [m for m in matches if m["match_score"] >= self.min_match_score]
            valid_matches.sort(key=lambda x: x["match_score"], reverse=True)
            return valid_matches
        except Exception as exc:
            self.logger.error(f"Error in find_property_matches: {exc}")
            return []

    def _get_properties_for_matching(self, property_ids: Optional[List[int]], limit: int) -> List[Property]:
        query = db.session.query(Property).filter(
            Property.status == "active",
            Property.is_deleted.is_(False),
        )
        if property_ids:
            query = query.filter(Property.id.in_(property_ids))
        query = query.order_by(Property.updated_at.desc())

        max_properties = int(os.environ.get("MATCHING_MAX_PROPERTIES", "5000"))
        if max_properties > 0 and not property_ids:
            query = query.limit(max_properties)
        return query.all()

    def _get_customers_for_matching(self, customer_ids: Optional[List[int]], limit: int) -> List[Customer]:
        # Include lead — kiosk/open-house often creates lead clients that still need matches
        query = db.session.query(Customer).filter(
            Customer.status.in_(["prospect", "active", "lead"]),
            Customer.is_deleted.is_(False),
        )
        if customer_ids:
            query = query.filter(Customer.id.in_(customer_ids))
        query = query.order_by(Customer.created_at.desc())

        max_customers = int(os.environ.get("MATCHING_MAX_CUSTOMERS", "2000"))
        if max_customers > 0 and not customer_ids:
            query = query.limit(max_customers)
        return query.all()

    def _batch_items(self, items: List, batch_size: int):
        for i in range(0, len(items), batch_size):
            yield items[i : i + batch_size]

    @staticmethod
    def _score_as_unit(raw) -> float:
        """Normalize engine scores to 0–1 (accepts 0–1 or 0–100)."""
        try:
            val = float(raw)
        except (TypeError, ValueError):
            return 0.0
        if val > 1.0:
            val = val / 100.0
        return max(0.0, min(1.0, val))

    def _process_property_customer_batch(self, properties: List[Property], customers: List[Customer]) -> List[Dict]:
        matches: List[Dict] = []

        for customer in customers:
            try:
                recommendations = gemini_service.get_property_recommendations(customer, properties)
                for rec in recommendations:
                    unit = self._score_as_unit(rec.get("match_score", rec.get("hybrid_score", 0)))
                    if unit >= self.min_match_score:
                        # Ensure create_match_record sees 0–100 style when needed
                        rec = dict(rec)
                        rec["match_score"] = unit * 100.0
                        match = self._create_match_record(customer, rec, properties)
                        if match:
                            matches.append(match)
            except Exception as exc:
                self.logger.error(f"Error processing customer {customer.id}: {exc}")
                matches.extend(self._fallback_matching(customer, properties))

        return matches

    def _process_customer_candidates(self, customer: Customer, candidates: List[Property]) -> List[Dict]:
        matches: List[Dict] = []
        try:
            recommendations = gemini_service.get_property_recommendations(customer, candidates)
            for rec in recommendations:
                unit = self._score_as_unit(rec.get("match_score", rec.get("hybrid_score", 0)))
                if unit >= self.min_match_score:
                    rec = dict(rec)
                    rec["match_score"] = unit * 100.0
                    match = self._create_match_record(customer, rec, candidates)
                    if match:
                        matches.append(match)
            # If AI/hybrid path returns nothing usable, fall back to rule scores on candidates
            if not matches and candidates:
                matches.extend(self._fallback_matching(customer, candidates))
        except Exception as exc:
            self.logger.error("Error processing customer %s candidates: %s", customer.id, exc)
            matches.extend(self._fallback_matching(customer, candidates))
        return matches

    def _dismissed_property_ids(self, customer_id: int) -> set:
        """Properties the agent/customer already dismissed — never re-match."""
        try:
            rows = (
                db.session.query(PropertyMatch.property_id)
                .filter(
                    PropertyMatch.customer_id == customer_id,
                    PropertyMatch.status == "dismissed",
                )
                .all()
            )
            return {r[0] for r in rows}
        except Exception as exc:
            self.logger.warning("Could not load dismissed matches for customer %s: %s", customer_id, exc)
            return set()

    def _passes_hard_filters(self, customer: Customer, prop: Property, dismissed: set) -> bool:
        """Hard gates before expensive scoring (budget, type, beds, location, dismissals)."""
        if prop.id in dismissed:
            return False
        if prop.price is not None and prop.price < 0:
            return False

        max_budget = customer.budget_max or 0
        min_budget = customer.budget_min or 0
        price = prop.price if prop.price is not None else 0
        max_budget_ok = (max_budget == 0) or (
            (price <= int(max_budget * 1.2))
            or (prop.rahn is not None and prop.rahn <= int(max_budget * 1.2))
        )
        min_budget_ok = (min_budget == 0) or (price >= int(min_budget * 0.5))
        if not (max_budget_ok and min_budget_ok):
            return False

        # Optional strict type
        preferred_type = (customer.preferred_type or "").strip().lower()
        strict_type = os.environ.get("MATCHING_STRICT_TYPE", "0") == "1"
        if preferred_type and strict_type:
            actual = (prop.property_type or "").strip().lower()
            if actual and preferred_type != actual and preferred_type not in actual:
                return False

        # Bedroom tolerance (default ±1 when preferred set)
        pref_beds = customer.preferred_bedrooms or 0
        if pref_beds > 0:
            tol = int(os.environ.get("MATCHING_BEDROOM_TOLERANCE", "1"))
            beds = prop.bedrooms or 0
            if abs(beds - pref_beds) > tol:
                return False

        # Optional strict location token match
        strict_loc = os.environ.get("MATCHING_STRICT_LOCATION", "0") == "1"
        loc_pref = (customer.location_preference or "").strip().lower()
        if strict_loc and loc_pref:
            hay = f"{prop.neighborhood or ''} {prop.address or ''}".lower()
            tokens = [t for t in loc_pref.replace(",", " ").split() if len(t) > 1]
            if tokens and not any(t in hay for t in tokens):
                return False

        return True

    def _prefilter_candidate_properties(self, customer: Customer, properties: List[Property]) -> List[Property]:
        top_n = int(os.environ.get("MATCHING_CANDIDATE_TOP_N", "15"))

        if not properties:
            return []

        dismissed = self._dismissed_property_ids(customer.id)
        hard_filtered = [
            prop for prop in properties if self._passes_hard_filters(customer, prop, dismissed)
        ]
        candidate_pool = hard_filtered if hard_filtered else []
        if not candidate_pool:
            return []

        try:
            ranked = vector_service.search_properties(customer, candidate_pool, top_k=top_n)
            ranked_properties = [item["property"] for item in ranked if item.get("property")]
            if ranked_properties:
                return ranked_properties[:top_n]
        except Exception as exc:
            self.logger.warning("Vector prefilter failed for customer %s: %s", customer.id, exc)

        return candidate_pool[:top_n]

    def _create_match_record(self, customer: Customer, recommendation: Dict, properties: List[Property]) -> Optional[Dict]:
        try:
            property_obj = recommendation.get("property")
            if not property_obj or not hasattr(property_obj, "id"):
                return None

            match_score_int = float(recommendation["match_score"])
            match_score = max(0.0, min(1.0, match_score_int / 100.0))

            confidence_level = "high" if match_score >= 0.8 else "medium" if match_score >= 0.6 else "low"
            priority = "high" if match_score >= self.high_priority_threshold else "normal"

            reasons = recommendation.get("pros") or recommendation.get("match_reasons") or []
            if not reasons and recommendation.get("analysis"):
                reasons = [
                    line.strip("- ")
                    for line in recommendation["analysis"].splitlines()
                    if line.strip().startswith("-")
                ]

            # Enrich with multi-parameter breakdown for agent-readable reasons
            try:
                breakdown = vector_service.score_breakdown(
                    customer, property_obj, float(recommendation.get("semantic_score") or match_score_int)
                )
                extra = vector_service._generate_match_reasons(
                    customer, property_obj, breakdown.get("semantic", match_score_int)
                )
                # Prefer concrete parameter reasons; keep unique order
                merged: List[str] = []
                for r in list(reasons) + list(extra):
                    if r and r not in merged:
                        merged.append(r)
                reasons = merged[:6]
            except Exception as exc:
                self.logger.debug("score breakdown enrich skipped: %s", exc)

            return {
                "property_id": property_obj.id,
                "customer_id": customer.id,
                "agent_id": property_obj.agent_id,
                "match_score": match_score,
                "confidence_level": confidence_level,
                "priority": priority,
                "match_reasons": json.dumps(reasons),
                "property": property_obj,
                "customer": customer,
            }
        except Exception as exc:
            self.logger.error(f"Error creating match record: {exc}")
            return None

    def _fallback_matching(self, customer: Customer, properties: List[Property]) -> List[Dict]:
        matches: List[Dict] = []
        try:
            dismissed = self._dismissed_property_ids(customer.id)
            for property_obj in properties:
                if not self._passes_hard_filters(customer, property_obj, dismissed):
                    continue
                breakdown = vector_service.score_breakdown(customer, property_obj, 50.0)
                score = breakdown["hybrid"] / 100.0
                if score >= self.min_match_score:
                    reasons = vector_service._generate_match_reasons(customer, property_obj, 50.0)
                    matches.append(
                        {
                            "property_id": property_obj.id,
                            "customer_id": customer.id,
                            "agent_id": property_obj.agent_id,
                            "match_score": score,
                            "confidence_level": "medium" if score >= 0.6 else "low",
                            "priority": "high" if score >= self.high_priority_threshold else "normal",
                            "match_reasons": json.dumps(reasons),
                            "property": property_obj,
                            "customer": customer,
                        }
                    )
        except Exception as exc:
            self.logger.error(f"Error in fallback matching: {exc}")
        return matches

    def _calculate_basic_match_score(self, customer: Customer, property_obj: Property) -> float:
        """0–1 score via multi-parameter hybrid (shared with vector_service)."""
        try:
            return vector_service.score_breakdown(customer, property_obj, 50.0)["hybrid"] / 100.0
        except Exception:
            return 0.0

    def save_matches_to_database(self, matches: List[Dict]) -> List[PropertyMatch]:
        """
        Persist matches. Sets transient attrs for notification layer:
          _notify_kind: "new" | "improved" | None
          _previous_score: float | None
        """
        saved_matches: List[PropertyMatch] = []

        try:
            for match_data in matches:
                agent_id = match_data.get("agent_id")
                # Prefer listing agent when match payload omits agent_id
                if not agent_id:
                    prop = match_data.get("property")
                    if prop is not None and getattr(prop, "agent_id", None):
                        agent_id = prop.agent_id

                existing_match = db.session.query(PropertyMatch).filter_by(
                    property_id=match_data["property_id"],
                    customer_id=match_data["customer_id"],
                ).first()

                if existing_match:
                    previous = float(existing_match.match_score or 0.0)
                    new_score = float(match_data["match_score"])
                    # Re-open dismissed matches if they score again
                    if existing_match.status == "dismissed":
                        existing_match.status = "pending"
                    if new_score > previous:
                        existing_match.match_score = new_score
                        existing_match.confidence_level = match_data["confidence_level"]
                        existing_match.priority = match_data["priority"]
                        existing_match.match_reasons = match_data["match_reasons"]
                        if agent_id and not existing_match.agent_id:
                            existing_match.agent_id = agent_id
                        existing_match._notify_kind = (  # type: ignore[attr-defined]
                            "improved" if (new_score - previous) >= self.score_improve_delta else None
                        )
                        existing_match._previous_score = previous  # type: ignore[attr-defined]
                    else:
                        # Still count as handled so UI does not show "0 saved"
                        existing_match.match_reasons = match_data.get(
                            "match_reasons", existing_match.match_reasons
                        )
                        existing_match._notify_kind = None  # type: ignore[attr-defined]
                        existing_match._previous_score = previous  # type: ignore[attr-defined]
                    saved_matches.append(existing_match)
                else:
                    new_match = PropertyMatch(
                        property_id=match_data["property_id"],
                        customer_id=match_data["customer_id"],
                        agent_id=agent_id,
                        match_score=match_data["match_score"],
                        confidence_level=match_data["confidence_level"],
                        priority=match_data["priority"],
                        match_reasons=match_data["match_reasons"],
                    )
                    new_match._notify_kind = "new"  # type: ignore[attr-defined]
                    new_match._previous_score = None  # type: ignore[attr-defined]
                    db.session.add(new_match)
                    saved_matches.append(new_match)

            db.session.commit()
            return saved_matches
        except Exception as exc:
            db.session.rollback()
            self.logger.error(f"Error saving matches: {exc}")
            return []

    def _resolve_notify_agent_id(self, match: PropertyMatch) -> Optional[int]:
        if match.agent_id:
            return match.agent_id
        property_obj = db.session.get(Property, match.property_id)
        if property_obj and property_obj.agent_id:
            match.agent_id = property_obj.agent_id
            return property_obj.agent_id
        return None

    def _has_unread_match_notification(self, agent_id: int, match_id: int) -> bool:
        if not self.notify_dedupe:
            return False
        return (
            db.session.query(AgentNotification.id)
            .filter(
                AgentNotification.agent_id == agent_id,
                AgentNotification.property_match_id == match_id,
                AgentNotification.status == "unread",
                AgentNotification.notification_type == "property_match",
            )
            .first()
            is not None
        )

    def create_agent_notifications(self, matches: List[PropertyMatch]) -> List[AgentNotification]:
        """
        Notify agents for new high matches or meaningful score improvements.
        Skips duplicates when an unread notification already exists for the match.
        """
        notifications: List[AgentNotification] = []

        if not matches:
            return notifications

        # Group by resolved agent
        matches_by_agent: Dict[int, List[PropertyMatch]] = {}
        for match in matches:
            if match.match_score < self.notification_threshold:
                continue
            kind = getattr(match, "_notify_kind", "new")
            # Only new matches or improved-by-delta get alerts (always-on, not noisy)
            if kind not in ("new", "improved"):
                continue
            agent_id = self._resolve_notify_agent_id(match)
            if not agent_id:
                continue
            if self._has_unread_match_notification(agent_id, match.id):
                self.logger.debug(
                    "Skip notify agent=%s match=%s (unread already exists)",
                    agent_id,
                    match.id,
                )
                continue
            matches_by_agent.setdefault(agent_id, []).append(match)

        for agent_id, agent_match_list in matches_by_agent.items():
            agent_notifications: List[AgentNotification] = []

            for match in agent_match_list:
                try:
                    notification = self._create_match_notification(agent_id, match)
                    if notification:
                        agent_notifications.append(notification)
                except Exception as e:
                    self.logger.error(
                        "Failed to create notification for agent %s, match %s: %s",
                        agent_id,
                        match.id,
                        e,
                    )

            if agent_notifications:
                try:
                    db.session.add_all(agent_notifications)
                    db.session.flush()
                    notifications.extend(agent_notifications)

                    for notification in agent_notifications:
                        try:
                            monitoring_service.log_notification_activity(
                                agent_id=agent_id,
                                notification_id=notification.id,
                                match_id=notification.property_match_id,
                            )
                        except Exception as e:
                            self.logger.error(
                                "Failed to log notification activity for notification %s: %s",
                                notification.id,
                                e,
                            )
                except Exception as e:
                    self.logger.error("Failed to save notifications for agent %s: %s", agent_id, e)
                    db.session.rollback()

        try:
            db.session.commit()
        except Exception as e:
            self.logger.error("Failed to commit notifications: %s", e)
            db.session.rollback()
            return []

        # Optional email for high-priority matches (off by default)
        if notifications and os.environ.get("MATCHER_EMAIL_ON_HIGH", "0") == "1":
            try:
                from services.notification_service import notification_service
                from sqlalchemy_models import Agent

                for note in notifications:
                    if note.priority != "high" or not note.property_match_id:
                        continue
                    match = db.session.get(PropertyMatch, note.property_match_id)
                    agent = db.session.get(Agent, note.agent_id)
                    if not match or not agent:
                        continue
                    prop = db.session.get(Property, match.property_id)
                    cust = db.session.get(Customer, match.customer_id)
                    if prop and cust:
                        notification_service._send_high_priority_email(
                            agent, note, match, prop, cust
                        )
            except Exception as exc:
                self.logger.debug("High-priority email hook skipped: %s", exc)

        return notifications

    def _format_money(self, value: Optional[float]) -> str:
        if value is None:
            return "n/a"
        try:
            return f"${float(value):,.0f}"
        except (TypeError, ValueError):
            return "n/a"

    def _create_match_notification(self, agent_id: int, match: PropertyMatch) -> Optional[AgentNotification]:
        try:
            customer = db.session.get(Customer, match.customer_id)
            property_obj = db.session.get(Property, match.property_id)
            if not customer or not property_obj:
                return None

            score_pct = int(round(match.match_score * 100))
            kind = getattr(match, "_notify_kind", "new")
            previous = getattr(match, "_previous_score", None)

            if kind == "improved" and previous is not None:
                prev_pct = int(round(float(previous) * 100))
                title = f"Match improved: {prev_pct}% → {score_pct}%"
            elif match.match_score >= self.high_priority_threshold:
                title = f"New best match ({score_pct}%)"
            else:
                title = f"New property match ({score_pct}%)"

            try:
                reasons = json.loads(match.match_reasons) if match.match_reasons else []
            except (json.JSONDecodeError, TypeError):
                reasons = [match.match_reasons] if match.match_reasons else []
            reasons_text = ", ".join(str(r) for r in reasons[:3]) if reasons else "preference alignment"

            addr = property_obj.address or property_obj.title or f"property #{property_obj.id}"
            message = (
                f"{customer.name} is a {score_pct}% match for {addr}. "
                f"Why: {reasons_text}. "
                f"Budget: {self._format_money(customer.budget_min)}–{self._format_money(customer.budget_max)}. "
                f"Price: {self._format_money(property_obj.price)}."
            )
            if kind == "improved" and previous is not None:
                message = f"Score rose from {int(round(float(previous) * 100))}%. " + message

            priority = "high" if match.match_score >= self.high_priority_threshold else "normal"

            return AgentNotification(
                agent_id=agent_id,
                property_match_id=match.id,
                title=title,
                message=message,
                notification_type="property_match",
                priority=priority,
            )
        except Exception as exc:
            self.logger.error(f"Error creating match notification: {exc}")
            return None

    def run_matching_cycle(
        self,
        property_ids: Optional[List[int]] = None,
        customer_ids: Optional[List[int]] = None,
        trigger_source: str = "scheduled",
        idempotency_key: Optional[str] = None,
    ) -> Dict:
        start_time = datetime.utcnow()
        idempotency_key = idempotency_key or self._build_idempotency_key(property_ids, customer_ids, trigger_source)

        session_id = monitoring_service.log_matching_job_start(
            f"matching_cycle_{int(start_time.timestamp())}",
            trigger_source,
        )

        try:
            run = self._begin_matching_run(idempotency_key, trigger_source, property_ids, customer_ids)
            if run is None:
                result = {
                    "status": "skipped",
                    "idempotency_key": idempotency_key,
                    "matches_found": 0,
                    "matches_saved": 0,
                    "notifications_created": 0,
                    "duration_seconds": 0,
                }
                monitoring_service.log_matching_job_completion(session_id, result, 0)
                return result

            matches = self.find_property_matches(property_ids, customer_ids)
            if not matches:
                duration = (datetime.utcnow() - start_time).total_seconds()
                result = {
                    "status": "completed",
                    "idempotency_key": idempotency_key,
                    "matches_found": 0,
                    "matches_saved": 0,
                    "notifications_created": 0,
                    "duration_seconds": duration,
                }
                run.status = "completed"
                run.finished_at = datetime.utcnow()
                run.result_summary = json.dumps(result)
                db.session.commit()
                monitoring_service.log_matching_job_completion(session_id, result, duration)
                return result

            saved_matches = self.save_matches_to_database(matches)
            notifications = self.create_agent_notifications(saved_matches)

            for notification in notifications:
                monitoring_service.log_notification_activity(
                    "created",
                    notification.agent_id,
                    notification.id,
                    {"match_score": notification.property_match.match_score if notification.property_match else None},
                )

            try:
                from services.automation_service import automation_service

                for match in saved_matches:
                    automation_service.handle_high_match_score(match)
            except Exception as exc:
                self.logger.warning(f"High-match automation failed: {exc}")

            duration = (datetime.utcnow() - start_time).total_seconds()
            result = {
                "status": "completed",
                "idempotency_key": idempotency_key,
                "matches_found": len(matches),
                "matches_saved": len(saved_matches),
                "notifications_created": len(notifications),
                "duration_seconds": duration,
                "high_priority_matches": len([m for m in matches if m["match_score"] >= self.high_priority_threshold]),
            }

            run.status = "completed"
            run.finished_at = datetime.utcnow()
            run.result_summary = json.dumps(result)
            db.session.commit()

            monitoring_service.log_matching_job_completion(session_id, result, duration)
            return result
        except Exception as exc:
            monitoring_service.log_matching_error(
                session_id,
                exc,
                {
                    "property_ids": property_ids,
                    "customer_ids": customer_ids,
                    "idempotency_key": idempotency_key,
                },
            )

            duration = (datetime.utcnow() - start_time).total_seconds()
            result = {
                "status": "error",
                "idempotency_key": idempotency_key,
                "error": str(exc),
                "duration_seconds": duration,
            }

            try:
                run = MatchingJobRun.query.filter_by(idempotency_key=idempotency_key).first()
                if run:
                    run.status = "failed"
                    run.finished_at = datetime.utcnow()
                    run.result_summary = json.dumps(result)
                    db.session.commit()
            except Exception:
                db.session.rollback()

            monitoring_service.log_matching_job_completion(session_id, result, duration)
            self.logger.error(f"Error in matching cycle: {exc}")
            return result


background_matcher = BackgroundMatcher()

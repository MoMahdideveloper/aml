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
        self.min_match_score = float(os.environ.get("MATCHER_MIN_SCORE", "0.5"))
        self.notification_threshold = float(os.environ.get("MATCHER_NOTIFICATION_THRESHOLD", "0.7"))
        self.high_priority_threshold = float(os.environ.get("MATCHER_HIGH_PRIORITY_THRESHOLD", "0.85"))

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
            "bucket": datetime.utcnow().strftime("%Y%m%d%H%M"),
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
        query = db.session.query(Customer).filter(
            Customer.status.in_(["prospect", "active"]),
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

    def _process_property_customer_batch(self, properties: List[Property], customers: List[Customer]) -> List[Dict]:
        matches: List[Dict] = []

        for customer in customers:
            try:
                recommendations = gemini_service.get_property_recommendations(customer, properties)
                for rec in recommendations:
                    if "match_score" in rec and rec["match_score"] >= self.min_match_score:
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
                if "match_score" in rec and rec["match_score"] >= self.min_match_score:
                    match = self._create_match_record(customer, rec, candidates)
                    if match:
                        matches.append(match)
        except Exception as exc:
            self.logger.error("Error processing customer %s candidates: %s", customer.id, exc)
            matches.extend(self._fallback_matching(customer, candidates))
        return matches

    def _prefilter_candidate_properties(self, customer: Customer, properties: List[Property]) -> List[Property]:
        top_n = int(os.environ.get("MATCHING_CANDIDATE_TOP_N", "15"))
        max_budget = customer.budget_max or 0
        min_budget = customer.budget_min or 0

        budget_filtered = [
            prop
            for prop in properties
            if (
                not max_budget
                or (prop.price is not None and prop.price <= int(max_budget * 1.2))
                or (prop.rahn is not None and prop.rahn <= int(max_budget * 1.2))
            )
            and (not min_budget or prop.price >= int(min_budget * 0.5))
        ]
        candidate_pool = budget_filtered
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

            reasons = recommendation.get("pros") or []
            if not reasons and recommendation.get("analysis"):
                reasons = [line.strip("- ") for line in recommendation["analysis"].splitlines() if line.strip().startswith("-")]

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
            for property_obj in properties:
                score = self._calculate_basic_match_score(customer, property_obj)
                if score >= self.min_match_score:
                    matches.append(
                        {
                            "property_id": property_obj.id,
                            "customer_id": customer.id,
                            "agent_id": property_obj.agent_id,
                            "match_score": score,
                            "confidence_level": "low",
                            "priority": "normal",
                            "match_reasons": json.dumps(["Basic preference matching"]),
                            "property": property_obj,
                            "customer": customer,
                        }
                    )
        except Exception as exc:
            self.logger.error(f"Error in fallback matching: {exc}")
        return matches

    def _calculate_basic_match_score(self, customer: Customer, property_obj: Property) -> float:
        # Calculate score for each category between 0 and 1, then average
        scores = []

        # Budget score
        if customer.budget_min is not None and customer.budget_max is not None and property_obj.price is not None:
            if customer.budget_min <= property_obj.price <= customer.budget_max:
                budget_score = 1.0
            elif property_obj.price <= customer.budget_max * 1.1:
                # Within 10% above max: give half credit (since full credit is 1.0)
                budget_score = 0.5
            else:
                budget_score = 0.0
            scores.append(budget_score)
        else:
            scores.append(0.0)

        # Bedrooms score
        if customer.preferred_bedrooms is not None and property_obj.bedrooms is not None:
            diff = abs(customer.preferred_bedrooms - property_obj.bedrooms)
            if diff == 0:
                bedroom_score = 1.0
            elif diff == 1:
                bedroom_score = 0.5
            else:
                bedroom_score = 0.0
            scores.append(bedroom_score)
        else:
            scores.append(0.0)

        # Bathrooms score
        if customer.preferred_bathrooms is not None and property_obj.bathrooms is not None:
            diff = abs(customer.preferred_bathrooms - property_obj.bathrooms)
            if diff == 0:
                bathroom_score = 1.0
            elif diff == 1:
                bathroom_score = 0.5
            else:
                bathroom_score = 0.0
            scores.append(bathroom_score)
        else:
            scores.append(0.0)

        # Property type score
        if customer.preferred_type is not None and property_obj.property_type is not None:
            if customer.preferred_type.lower() == property_obj.property_type.lower():
                type_score = 1.0
            else:
                type_score = 0.0
            scores.append(type_score)
        else:
            scores.append(0.0)

        # Average the four scores
        return sum(scores) / len(scores)

    def save_matches_to_database(self, matches: List[Dict]) -> List[PropertyMatch]:
        saved_matches: List[PropertyMatch] = []

        try:
            for match_data in matches:
                existing_match = db.session.query(PropertyMatch).filter_by(
                    property_id=match_data["property_id"],
                    customer_id=match_data["customer_id"],
                ).first()

                if existing_match:
                    if match_data["match_score"] > existing_match.match_score:
                        existing_match.match_score = match_data["match_score"]
                        existing_match.confidence_level = match_data["confidence_level"]
                        existing_match.priority = match_data["priority"]
                        existing_match.match_reasons = match_data["match_reasons"]
                        saved_matches.append(existing_match)
                else:
                    new_match = PropertyMatch(
                        property_id=match_data["property_id"],
                        customer_id=match_data["customer_id"],
                        agent_id=match_data["agent_id"],
                        match_score=match_data["match_score"],
                        confidence_level=match_data["confidence_level"],
                        priority=match_data["priority"],
                        match_reasons=match_data["match_reasons"],
                    )
                    db.session.add(new_match)
                    saved_matches.append(new_match)

            db.session.commit()
            return saved_matches
        except Exception as exc:
            db.session.rollback()
            self.logger.error(f"Error saving matches: {exc}")
            return []

    def create_agent_notifications(self, matches: List[PropertyMatch]) -> List[AgentNotification]:
        notifications: List[AgentNotification] = []

        try:
            agent_matches: Dict[int, List[PropertyMatch]] = {}
            for match in matches:
                if match.match_score >= self.notification_threshold and match.agent_id:
                    agent_matches.setdefault(match.agent_id, []).append(match)

            for agent_id, agent_match_list in agent_matches.items():
                for match in agent_match_list:
                    notification = self._create_match_notification(agent_id, match)
                    if notification:
                        notifications.append(notification)

            for notification in notifications:
                db.session.add(notification)

            db.session.commit()
            return notifications
        except Exception as exc:
            db.session.rollback()
            self.logger.error(f"Error creating notifications: {exc}")
            return []

    def _create_match_notification(self, agent_id: int, match: PropertyMatch) -> Optional[AgentNotification]:
        try:
            customer = db.session.get(Customer, match.customer_id)
            property_obj = db.session.get(Property, match.property_id)
            if not customer or not property_obj:
                return None

            score_pct = int(match.match_score * 100)
            title = f"High-Quality Match Found ({score_pct}%)"
            reasons = json.loads(match.match_reasons) if match.match_reasons else []
            reasons_text = ", ".join(reasons[:3])

            message = (
                f"Customer {customer.name} is a {score_pct}% match for property at {property_obj.address}. "
                f"Match reasons: {reasons_text}. Customer budget: ${customer.budget_min:,.0f}-${customer.budget_max:,.0f}. "
                f"Property price: ${property_obj.price:,.0f}."
            )
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

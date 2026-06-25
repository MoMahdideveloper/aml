import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

from sqlalchemy import or_

from sqlalchemy_models import Agent, Customer, Deal, Property, Task
from services.database_service import database_service
from services.maskan_live_service import maskan_live_service
from services.vector_service import vector_service
from utils.execution_tracer import log_execution


class SearchService:
    """Hybrid property ranking with deterministic keyword-only degradation."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("services.search_service")
        self.hybrid_weights = {
            "semantic": 0.70,
            "keyword": 0.30,
        }

    @log_execution
    def search_properties(
        self,
        customer: Customer,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        bundle = self.search_properties_with_meta(customer=customer, top_k=top_k)
        return bundle.get("results", [])

    @log_execution
    def search_properties_with_meta(
        self,
        customer: Customer,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        try:
            property_candidates = database_service.get_properties(
                min_price=customer.budget_min,
                max_price=customer.budget_max * 1.2 if customer.budget_max else None,
                status="active",
            )
            if not property_candidates:
                return {
                    "results": [],
                    "meta": {
                        "mode": "keyword_only",
                        "is_fallback": True,
                        "fallback_reason": "no_active_properties",
                    },
                }

            properties_by_id = {prop.id: prop for prop in property_candidates if getattr(prop, "id", None) is not None}
            if not properties_by_id:
                return {
                    "results": [],
                    "meta": {
                        "mode": "keyword_only",
                        "is_fallback": True,
                        "fallback_reason": "no_valid_property_ids",
                    },
                }

            keyword_scores = {
                property_id: self._calculate_keyword_score(customer, prop)
                for property_id, prop in properties_by_id.items()
            }
            vector_scores, vector_meta = self._get_vector_scores(
                customer=customer,
                properties=list(properties_by_id.values()),
                top_k=max(top_k * 3, 20),
            )

            use_hybrid = bool(vector_scores) and not bool(vector_meta.get("is_fallback", False))
            ranked: List[Tuple[Property, float, float, float]] = []
            for property_id, prop in properties_by_id.items():
                keyword_score = keyword_scores.get(property_id, 0.0)
                semantic_score = vector_scores.get(property_id, 0.0) if use_hybrid else 0.0
                if use_hybrid:
                    total_score = (
                        semantic_score * self.hybrid_weights["semantic"]
                        + keyword_score * self.hybrid_weights["keyword"]
                    )
                else:
                    total_score = keyword_score
                ranked.append((prop, total_score, semantic_score, keyword_score))

            ranked.sort(key=self._ranking_sort_key)

            results = [
                {
                    "property": prop,
                    "hybrid_score": total_score * 100.0,
                    "semantic_score": semantic_score * 100.0,
                    "keyword_score": keyword_score * 100.0,
                    "match_reasons": self._generate_hybrid_reasons(customer, prop),
                }
                for prop, total_score, semantic_score, keyword_score in ranked[:top_k]
            ]

            meta = {
                "mode": "hybrid" if use_hybrid else "keyword_only",
                "is_fallback": not use_hybrid,
                "fallback_reason": None if use_hybrid else (vector_meta.get("reason") or "vector_unavailable"),
            }
            return {"results": results, "meta": meta}
        except Exception as exc:
            self.logger.error(f"Error in hybrid search: {exc}")
            return {
                "results": [],
                "meta": {
                    "mode": "keyword_only",
                    "is_fallback": True,
                    "fallback_reason": "search_exception",
                },
            }

    @log_execution
    def _get_vector_scores(
        self,
        customer: Customer,
        properties: List[Property],
        top_k: int,
    ) -> Tuple[Dict[int, float], Dict[str, Any]]:
        try:
            vector_response: Any
            if hasattr(vector_service, "search_properties_with_meta"):
                vector_response = vector_service.search_properties_with_meta(customer, properties, top_k=top_k)
            else:
                vector_response = {
                    "results": vector_service.search_properties(customer, properties, top_k=top_k),
                    "meta": {
                        "mode": "legacy",
                        "is_fallback": False,
                    },
                }

            if not isinstance(vector_response, dict):
                return {}, {"is_fallback": True, "reason": "invalid_vector_response", "mode": "unavailable"}

            vector_results = vector_response.get("results", [])
            vector_meta = vector_response.get("meta", {}) if isinstance(vector_response.get("meta"), dict) else {}
            if not isinstance(vector_results, list):
                return {}, {"is_fallback": True, "reason": "invalid_vector_result_format", "mode": "unavailable"}

            if vector_meta.get("is_fallback"):
                return {}, vector_meta

            semantic_scores: Dict[int, float] = {}
            for item in vector_results:
                if not isinstance(item, dict):
                    continue
                prop = item.get("property")
                property_id = getattr(prop, "id", None)
                if property_id is None:
                    continue
                semantic_score = self._normalize_score(item.get("semantic_score", 0.0))
                semantic_scores[int(property_id)] = max(
                    semantic_scores.get(int(property_id), 0.0),
                    semantic_score,
                )

            if not semantic_scores:
                return {}, {"is_fallback": True, "reason": "empty_vector_results", "mode": vector_meta.get("mode", "unavailable")}
            return semantic_scores, vector_meta
        except Exception as exc:
            self.logger.warning("Vector search failed, degrading to keyword-only: %s", exc)
            return {}, {"is_fallback": True, "reason": "vector_exception", "mode": "unavailable"}

    @log_execution
    def _normalize_score(self, raw_score: Any) -> float:
        try:
            numeric = float(raw_score)
        except (TypeError, ValueError):
            return 0.0
        if numeric > 1.0:
            numeric = numeric / 100.0
        return max(0.0, min(1.0, numeric))

    @log_execution
    def _calculate_keyword_score(self, customer: Customer, property_obj: Property) -> float:
        weights = {
            "budget": 0.40,
            "bedrooms": 0.20,
            "bathrooms": 0.15,
            "type": 0.15,
            "location": 0.10,
        }
        score = 0.0
        weight_sum = 0.0

        budget_score = self._budget_score(customer, property_obj)
        if budget_score is not None:
            score += budget_score * weights["budget"]
            weight_sum += weights["budget"]

        bedroom_score = self._distance_score(
            target=getattr(customer, "preferred_bedrooms", 0),
            actual=getattr(property_obj, "bedrooms", 0),
        )
        if bedroom_score is not None:
            score += bedroom_score * weights["bedrooms"]
            weight_sum += weights["bedrooms"]

        bathroom_score = self._distance_score(
            target=getattr(customer, "preferred_bathrooms", 0),
            actual=getattr(property_obj, "bathrooms", 0),
        )
        if bathroom_score is not None:
            score += bathroom_score * weights["bathrooms"]
            weight_sum += weights["bathrooms"]

        preferred_type = (getattr(customer, "preferred_type", "") or "").strip().lower()
        property_type = (getattr(property_obj, "property_type", "") or "").strip().lower()
        if preferred_type:
            score += (1.0 if preferred_type == property_type else 0.0) * weights["type"]
            weight_sum += weights["type"]

        preferred_location = (getattr(customer, "location_preference", "") or "").strip().lower()
        property_location = (getattr(property_obj, "neighborhood", "") or "").strip().lower()
        if preferred_location:
            location_match = 1.0 if property_location and property_location in preferred_location else 0.0
            score += location_match * weights["location"]
            weight_sum += weights["location"]

        if weight_sum == 0:
            return 0.5
        return max(0.0, min(1.0, score / weight_sum))

    @log_execution
    def _budget_score(self, customer: Customer, property_obj: Property) -> float:
        budget_min = float(getattr(customer, "budget_min", 0) or 0)
        budget_max = float(getattr(customer, "budget_max", 0) or 0)
        price = float(getattr(property_obj, "price", 0) or 0)
        if price <= 0 or (budget_min <= 0 and budget_max <= 0):
            return 0.5
        if budget_min > 0 and budget_max > 0 and budget_min <= price <= budget_max:
            return 1.0
        if budget_max > 0 and price <= budget_max * 1.1:
            return 0.75
        if budget_max > 0 and price <= budget_max * 1.2:
            return 0.5
        if budget_min > 0 and price >= budget_min * 0.9:
            return 0.4
        return 0.1

    @log_execution
    def _distance_score(self, target: Any, actual: Any) -> float:
        try:
            target_value = float(target or 0)
            actual_value = float(actual or 0)
        except (TypeError, ValueError):
            return 0.0
        if target_value <= 0:
            return 0.5
        distance = abs(target_value - actual_value)
        if distance == 0:
            return 1.0
        if distance <= 1:
            return 0.75
        if distance <= 2:
            return 0.4
        return 0.1

    @log_execution
    def _ranking_sort_key(self, item: Tuple[Property, float, float, float]) -> Tuple[float, float, float, int]:
        prop, total_score, _, _ = item
        property_rating = float(getattr(prop, "rating", 0.0) or 0.0)
        nightly_price = float(getattr(prop, "nightly_price", getattr(prop, "price", float("inf"))) or float("inf"))
        property_id = int(getattr(prop, "id", 0) or 0)
        # Deterministic tie-break order:
        # total_score DESC -> property_rating DESC -> nightly_price ASC -> property_id ASC
        return (-round(total_score, 8), -round(property_rating, 8), nightly_price, property_id)

    @log_execution
    def _generate_hybrid_reasons(self, customer: Customer, property_obj: Property) -> List[str]:
        reasons: List[str] = []
        if customer.budget_max and property_obj.price <= customer.budget_max:
            reasons.append("Within budget")
        if property_obj.bedrooms == customer.preferred_bedrooms:
            reasons.append("Exact bedroom match")
        if (property_obj.property_type or "").lower() == (customer.preferred_type or "").lower():
            reasons.append(f"Matches preferred type ({property_obj.property_type})")
        if (
            property_obj.neighborhood
            and customer.location_preference
            and property_obj.neighborhood.lower() in customer.location_preference.lower()
        ):
            reasons.append("Preferred location")
        return reasons


search_service = SearchService()

@log_execution
def _safe_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


@log_execution
def execute_property_search(
    beds: int | None = None,
    sqm: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    property_type: str | None = None,
    location: str | None = None,
    keyword: str | None = None,
    listing_type: str | None = None,
    min_parking: int | None = None,
    min_floors: int | None = None,
    has_elevator: bool | None = None,
    has_storage: bool | None = None,
    document_type: str | None = None,
    floor_covering: str | None = None,
    facade_type: str | None = None,
    heating_type: str | None = None,
    cooling_type: str | None = None,
    property_direction: str | None = None,
    min_land_area: int | None = None,
    min_year_built: int | None = None,
    property_category: str | None = None,
    is_exchangeable: bool | None = None,
    file_code: str | None = None,
    max_rahn: int | None = None,
    max_ejare: int | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Deterministic SQL search used by Agentic-RAG tool-calls."""
    limit = max(1, min(_safe_int(top_k) or 5, 20))
    query = Property.query.filter(Property.is_deleted.is_(False)).filter(Property.status == "active")

    # ── Core numeric filters ──────────────────────────────────────────────
    min_beds = _safe_int(beds)
    min_sqm = _safe_int(sqm)
    min_price_val = _safe_int(min_price)
    max_price_val = _safe_int(max_price)

    if min_beds is not None:
        query = query.filter(Property.bedrooms >= min_beds)
    if min_sqm is not None:
        query = query.filter(Property.square_feet >= min_sqm)
    if min_price_val is not None:
        query = query.filter(Property.price >= min_price_val)
    if max_price_val is not None:
        query = query.filter(Property.price <= max_price_val)

    # ── Text filters ──────────────────────────────────────────────────────
    normalized_type = (property_type or "").strip().lower()
    if normalized_type:
        query = query.filter(Property.property_type.ilike(f"%{normalized_type}%"))

    normalized_location = (location or "").strip()
    if normalized_location:
        query = query.filter(
            or_(
                Property.neighborhood.ilike(f"%{normalized_location}%"),
                Property.address.ilike(f"%{normalized_location}%"),
            )
        )

    normalized_keyword = (keyword or "").strip()
    if normalized_keyword:
        kw_filter = f"%{normalized_keyword}%"
        query = query.filter(
            or_(
                Property.title.ilike(kw_filter),
                Property.description.ilike(kw_filter),
                Property.address.ilike(kw_filter),
                Property.property_features.ilike(kw_filter),
            )
        )

    # ── Listing type (sale / rental) ──────────────────────────────────────
    normalized_listing = (listing_type or "").strip().lower()
    if normalized_listing:
        query = query.filter(Property.listing_type.ilike(normalized_listing))

    # ── Parking & floors ──────────────────────────────────────────────────
    min_parking_val = _safe_int(min_parking)
    if min_parking_val is not None:
        query = query.filter(Property.parking_spaces >= min_parking_val)

    min_floors_val = _safe_int(min_floors)
    if min_floors_val is not None:
        query = query.filter(Property.floors >= min_floors_val)

    # ── Boolean amenities ─────────────────────────────────────────────────
    if has_elevator is True:
        query = query.filter(Property.has_elevator.is_(True))
    if has_storage is True:
        query = query.filter(Property.has_storage.is_(True))
    if is_exchangeable is True:
        query = query.filter(Property.is_exchangeable.is_(True))

    # ── String attribute filters ──────────────────────────────────────────
    for attr_name, attr_value in [
        ("document_type", document_type),
        ("floor_covering", floor_covering),
        ("facade_type", facade_type),
        ("heating_type", heating_type),
        ("cooling_type", cooling_type),
        ("property_direction", property_direction),
        ("property_category", property_category),
    ]:
        normalized = (attr_value or "").strip()
        if normalized:
            query = query.filter(getattr(Property, attr_name).ilike(f"%{normalized}%"))

    # ── Land area & year built ────────────────────────────────────────────
    min_land_val = _safe_int(min_land_area)
    if min_land_val is not None:
        query = query.filter(Property.land_area >= min_land_val)

    min_year_val = _safe_int(min_year_built)
    if min_year_val is not None:
        query = query.filter(Property.year_built >= min_year_val)

    # ── File code (exact prefix match) ────────────────────────────────────
    normalized_file_code = (file_code or "").strip()
    if normalized_file_code:
        query = query.filter(Property.file_code.ilike(f"{normalized_file_code}%"))

    # ── Rental pricing (rahn / ejare) ─────────────────────────────────────
    max_rahn_val = _safe_int(max_rahn)
    if max_rahn_val is not None:
        query = query.filter(Property.rahn.isnot(None)).filter(Property.rahn <= max_rahn_val)

    max_ejare_val = _safe_int(max_ejare)
    if max_ejare_val is not None:
        query = query.filter(Property.ejare.isnot(None)).filter(Property.ejare <= max_ejare_val)

    # ── Execute & format ──────────────────────────────────────────────────
    properties = query.order_by(Property.created_at.desc(), Property.id.desc()).limit(limit).all()

    formatted: list[dict] = []
    for prop in properties:
        description = prop.description or ""
        entry: dict = {
            "id": prop.id,
            "title": prop.title,
            "property_type": prop.property_type,
            "listing_type": prop.listing_type,
            "price": prop.price,
            "bedrooms": prop.bedrooms,
            "bathrooms": prop.bathrooms,
            "square_feet": prop.square_feet,
            "neighborhood": prop.neighborhood,
            "description": f"{description[:200]}..." if len(description) > 200 else description,
            "source": "local",
        }
        # Include extra detail when present
        if prop.parking_spaces:
            entry["parking_spaces"] = prop.parking_spaces
        if prop.has_elevator:
            entry["has_elevator"] = True
        if prop.has_storage:
            entry["has_storage"] = True
        if prop.floors and prop.floors > 1:
            entry["floors"] = prop.floors
        if prop.land_area:
            entry["land_area"] = prop.land_area
        if prop.year_built:
            entry["year_built"] = prop.year_built
        if prop.heating_type:
            entry["heating_type"] = prop.heating_type
        if prop.cooling_type:
            entry["cooling_type"] = prop.cooling_type
        if prop.document_type:
            entry["document_type"] = prop.document_type
        if prop.rahn:
            entry["rahn"] = prop.rahn
        if prop.ejare:
            entry["ejare"] = prop.ejare
        if prop.file_code:
            entry["file_code"] = prop.file_code
        formatted.append(entry)

    # Optional live merge from external Maskan API service.
    if maskan_live_service.is_enabled:
        try:
            external_rows = maskan_live_service.search_properties(
                beds=min_beds,
                sqm=min_sqm,
                min_price=min_price_val,
                max_price=max_price_val,
                property_type=normalized_type or None,
                location=normalized_location or None,
                top_k=limit,
            )
            dedupe_keys = {
                (
                    str(item.get("title") or "").strip().lower(),
                    _safe_int(item.get("price")) or 0,
                    _safe_int(item.get("square_feet")) or 0,
                )
                for item in formatted
            }
            for row in external_rows:
                key = (
                    str(row.get("title") or "").strip().lower(),
                    _safe_int(row.get("price")) or 0,
                    _safe_int(row.get("square_feet")) or 0,
                )
                if key in dedupe_keys:
                    continue
                dedupe_keys.add(key)
                formatted.append(row)
        except Exception as exc:
            logging.getLogger("services.search_service").warning("External Maskan search failed: %s", exc)

    return formatted[:limit]


@log_execution
def _customer_priority_hint(customer: Customer) -> str:
    budget_max = float(getattr(customer, "budget_max", 0) or 0)
    if budget_max >= 1_000_000:
        return "high"
    if budget_max >= 400_000:
        return "medium"
    return "normal"


@log_execution
def execute_customer_search(
    intent_type: str | None = None,
    min_budget: int | None = None,
    max_budget: int | None = None,
    preferred_beds: int | None = None,
    location: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Deterministic customer retrieval used by Agentic-RAG tool-calls."""
    query = Customer.query.filter(Customer.is_deleted.is_(False)).filter(Customer.status == "active")
    limit = max(1, min(_safe_int(top_k) or 5, 20))

    min_budget_val = _safe_int(min_budget)
    max_budget_val = _safe_int(max_budget)
    preferred_beds_val = _safe_int(preferred_beds)
    normalized_intent = (intent_type or "").strip().lower()
    normalized_location = (location or "").strip()

    if min_budget_val is not None:
        query = query.filter(Customer.budget_max >= min_budget_val)
    if max_budget_val is not None:
        query = query.filter(Customer.budget_min <= max_budget_val)
    if preferred_beds_val is not None:
        query = query.filter(Customer.preferred_bedrooms >= preferred_beds_val)
    if normalized_location:
        query = query.filter(Customer.location_preference.ilike(f"%{normalized_location}%"))

    if normalized_intent in {"investor", "investment"}:
        query = query.filter(Customer.preferred_type.ilike("%investment%"))
    elif normalized_intent in {"first_time_buyer", "first-time-buyer", "first time buyer"}:
        query = query.filter(Customer.preferences.ilike("%first%"))

    customers = query.order_by(Customer.budget_max.desc(), Customer.created_at.desc()).limit(limit).all()
    return [
        {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "budget_min": customer.budget_min,
            "budget_max": customer.budget_max,
            "preferred_bedrooms": customer.preferred_bedrooms,
            "preferred_bathrooms": customer.preferred_bathrooms,
            "preferred_type": customer.preferred_type,
            "location_preference": customer.location_preference,
            "status": customer.status,
            "priority_hint": _customer_priority_hint(customer),
        }
        for customer in customers
    ]


@log_execution
def _parse_iso_date(value: Any):
    raw = str(value or "").strip()
    if not raw:
        return None
    # Support plain date and full datetime forms.
    for candidate in (raw, f"{raw}T00:00:00"):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return None


@log_execution
def execute_deal_search(
    status: str | None = None,
    min_offer: int | None = None,
    max_offer: int | None = None,
    customer_name: str | None = None,
    property_title: str | None = None,
    agent_name: str | None = None,
    keyword: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Deterministic deal retrieval with relational filters."""
    limit = max(1, min(_safe_int(top_k) or 5, 20))
    query = Deal.query.filter(Deal.is_deleted.is_(False))

    needs_customer_join = bool(customer_name or keyword)
    needs_property_join = bool(property_title or keyword)
    needs_agent_join = bool(agent_name or keyword)

    if needs_customer_join:
        query = query.join(Deal.customer)
    if needs_property_join:
        query = query.join(Deal.property)
    if needs_agent_join:
        query = query.outerjoin(Deal.agent)

    normalized_status = (status or "").strip().lower()
    if normalized_status:
        query = query.filter(Deal.status.ilike(normalized_status))

    min_offer_val = _safe_int(min_offer)
    max_offer_val = _safe_int(max_offer)
    if min_offer_val is not None:
        query = query.filter(Deal.offer_amount >= min_offer_val)
    if max_offer_val is not None:
        query = query.filter(Deal.offer_amount <= max_offer_val)

    normalized_customer = (customer_name or "").strip()
    if normalized_customer:
        query = query.filter(Customer.name.ilike(f"%{normalized_customer}%"))

    normalized_property = (property_title or "").strip()
    if normalized_property:
        query = query.filter(Property.title.ilike(f"%{normalized_property}%"))

    normalized_agent = (agent_name or "").strip()
    if normalized_agent:
        query = query.filter(Agent.name.ilike(f"%{normalized_agent}%"))

    normalized_keyword = (keyword or "").strip()
    if normalized_keyword:
        keyword_filter = f"%{normalized_keyword}%"
        query = query.filter(
            or_(
                Deal.notes.ilike(keyword_filter),
                Deal.status.ilike(keyword_filter),
                Customer.name.ilike(keyword_filter) if needs_customer_join else False,
                Property.title.ilike(keyword_filter) if needs_property_join else False,
                Agent.name.ilike(keyword_filter) if needs_agent_join else False,
            )
        )

    deals = query.order_by(Deal.updated_at.desc(), Deal.id.desc()).limit(limit).all()
    results: list[dict] = []
    for deal in deals:
        notes = deal.notes or ""
        results.append(
            {
                "id": deal.id,
                "status": deal.status,
                "offer_amount": deal.offer_amount,
                "customer_id": deal.customer_id,
                "customer_name": deal.customer.name if deal.customer else None,
                "property_id": deal.property_id,
                "property_title": deal.property.title if deal.property else None,
                "agent_id": deal.agent_id,
                "agent_name": deal.agent.name if deal.agent else None,
                "notes": f"{notes[:200]}..." if len(notes) > 200 else notes,
                "created_at": deal.created_at.isoformat() if deal.created_at else None,
                "updated_at": deal.updated_at.isoformat() if deal.updated_at else None,
            }
        )
    return results


@log_execution
def execute_task_search(
    status: str | None = None,
    priority: str | None = None,
    agent_name: str | None = None,
    due_before: str | None = None,
    due_after: str | None = None,
    keyword: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Deterministic task retrieval with status/priority/date filters."""
    limit = max(1, min(_safe_int(top_k) or 5, 20))
    query = Task.query.filter(Task.is_deleted.is_(False))

    needs_agent_join = bool(agent_name or keyword)
    if needs_agent_join:
        query = query.join(Task.agent)

    normalized_status = (status or "").strip().lower()
    if normalized_status:
        query = query.filter(Task.status.ilike(normalized_status))

    normalized_priority = (priority or "").strip().lower()
    if normalized_priority:
        query = query.filter(Task.priority.ilike(normalized_priority))

    due_before_dt = _parse_iso_date(due_before)
    due_after_dt = _parse_iso_date(due_after)
    if due_before_dt is not None:
        query = query.filter(Task.due_date.isnot(None)).filter(Task.due_date <= due_before_dt)
    if due_after_dt is not None:
        query = query.filter(Task.due_date.isnot(None)).filter(Task.due_date >= due_after_dt)

    normalized_agent = (agent_name or "").strip()
    if normalized_agent:
        query = query.filter(Agent.name.ilike(f"%{normalized_agent}%"))

    normalized_keyword = (keyword or "").strip()
    if normalized_keyword:
        keyword_filter = f"%{normalized_keyword}%"
        query = query.filter(
            or_(
                Task.title.ilike(keyword_filter),
                Task.description.ilike(keyword_filter),
                Task.status.ilike(keyword_filter),
                Task.priority.ilike(keyword_filter),
                Agent.name.ilike(keyword_filter) if needs_agent_join else False,
            )
        )

    tasks = query.order_by(Task.due_date.is_(None), Task.due_date.asc(), Task.created_at.desc(), Task.id.desc()).limit(limit).all()
    results: list[dict] = []
    for task in tasks:
        description = task.description or ""
        results.append(
            {
                "id": task.id,
                "title": task.title,
                "description": f"{description[:200]}..." if len(description) > 200 else description,
                "priority": task.priority,
                "status": task.status,
                "due_date": task.due_date.isoformat() if task.due_date else None,
                "agent_id": task.agent_id,
                "agent_name": task.agent.name if task.agent else None,
                "created_at": task.created_at.isoformat() if task.created_at else None,
            }
        )
    return results


@log_execution
def execute_agent_search(
    name: str | None = None,
    specialization: str | None = None,
    min_total_sales: int | None = None,
    min_active_listings: int | None = None,
    keyword: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Deterministic agent retrieval with performance filters."""
    limit = max(1, min(_safe_int(top_k) or 5, 20))
    query = Agent.query.filter(Agent.is_deleted.is_(False))

    normalized_name = (name or "").strip()
    if normalized_name:
        query = query.filter(Agent.name.ilike(f"%{normalized_name}%"))

    normalized_spec = (specialization or "").strip()
    if normalized_spec:
        query = query.filter(Agent.specialization.ilike(f"%{normalized_spec}%"))

    min_sales_val = _safe_int(min_total_sales)
    if min_sales_val is not None:
        query = query.filter(Agent.total_sales >= min_sales_val)

    min_listings_val = _safe_int(min_active_listings)
    if min_listings_val is not None:
        query = query.filter(Agent.active_listings >= min_listings_val)

    normalized_keyword = (keyword or "").strip()
    if normalized_keyword:
        keyword_filter = f"%{normalized_keyword}%"
        query = query.filter(
            or_(
                Agent.name.ilike(keyword_filter),
                Agent.email.ilike(keyword_filter),
                Agent.phone.ilike(keyword_filter),
                Agent.specialization.ilike(keyword_filter),
                Agent.bio.ilike(keyword_filter),
            )
        )

    agents = query.order_by(Agent.total_sales.desc(), Agent.active_listings.desc(), Agent.id.desc()).limit(limit).all()
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "email": agent.email,
            "phone": agent.phone,
            "specialization": agent.specialization,
            "total_sales": agent.total_sales,
            "active_listings": agent.active_listings,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
        }
        for agent in agents
    ]

import hashlib
import json
import logging
import math
import os
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import bindparam, text

from database import db
from utils.execution_tracer import log_execution

from sqlalchemy_models import Customer, Property, PropertyEmbedding
from services.embeddings import embedding_provider
from services.proptech_scoring import (
    build_neighborhood_price_per_sqm,
    build_recent_favorites_map,
    get_customer_score,
    get_property_score,
)


class VectorService:
    """
    Vector recommendation service using DB-backed embeddings.
    Supports optional pgvector nearest-neighbor queries on Postgres.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("services.vector_service")
        self.vector_distance = os.environ.get("VECTOR_DISTANCE", "cosine").lower()
        self.embedding_dim = int(os.environ.get("EMBEDDING_DIM", "768"))
        self._pgvector_column_available: Optional[bool] = None

        # Hybrid weights (sum = 1.0). More parameters = better agent-facing scores.
        # Legacy REQUIREMENTS_WEIGHT still supported (split into type + rooms).
        raw = {
            "semantic": float(os.environ.get("SEMANTIC_WEIGHT", "0.35")),
            "budget": float(os.environ.get("BUDGET_WEIGHT", "0.20")),
            "location": float(os.environ.get("LOCATION_WEIGHT", "0.15")),
            "type": float(os.environ.get("TYPE_WEIGHT", "0.10")),
            "rooms": float(os.environ.get("ROOMS_WEIGHT", "0.10")),
            "amenities": float(os.environ.get("AMENITIES_WEIGHT", "0.05")),
            "size": float(os.environ.get("SIZE_WEIGHT", "0.05")),
        }
        legacy_req = os.environ.get("REQUIREMENTS_WEIGHT")
        if legacy_req is not None and os.environ.get("TYPE_WEIGHT") is None and os.environ.get("ROOMS_WEIGHT") is None:
            # Old 3-knob config: map requirements into type+rooms and keep semantic/budget
            try:
                req = float(legacy_req)
                raw["type"] = req * 0.5
                raw["rooms"] = req * 0.5
            except ValueError:
                pass
        total = sum(max(0.0, v) for v in raw.values())
        if total > 0:
            self.weights = {k: max(0.0, v) / total for k, v in raw.items()}
        else:
            self.weights = {
                "semantic": 0.35,
                "budget": 0.20,
                "location": 0.15,
                "type": 0.10,
                "rooms": 0.10,
                "amenities": 0.05,
                "size": 0.05,
            }

    @log_execution
    def _create_property_text(self, property_obj: Property) -> str:
        price_range = self._get_price_range_description(property_obj.price)
        features = property_obj.property_features if property_obj.property_features else "standard features"
        condition = property_obj.property_condition or "well-maintained"
        return (
            f"A {condition} {property_obj.property_type} in {property_obj.neighborhood or 'prime area'} at {property_obj.address}. "
            f"It has {property_obj.bedrooms} bedrooms, {property_obj.bathrooms} bathrooms, {property_obj.square_feet} sqft. "
            f"Price {property_obj.price} ({price_range}). Features: {features}. Description: {property_obj.description}."
        )

    @log_execution
    def _create_customer_text(self, customer: Customer) -> str:
        midpoint = (
            (customer.budget_min + customer.budget_max) / 2
            if customer.budget_max
            else customer.budget_min
        )
        budget_range = self._get_price_range_description(midpoint)
        return (
            f"Looking for {customer.preferred_type} with {customer.preferred_bedrooms} bedrooms and "
            f"{customer.preferred_bathrooms} bathrooms in {customer.location_preference}. "
            f"Budget around {budget_range}."
        )

    @log_execution
    def _get_price_range_description(self, price: float) -> str:
        if price < 200000:
            return "budget-friendly"
        if price < 400000:
            return "moderately priced"
        if price < 700000:
            return "upper-middle"
        if price < 1000000:
            return "high-end"
        return "luxury"

    @log_execution
    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        length = min(len(vec_a), len(vec_b))
        if length == 0:
            return 0.0
        dot = sum(vec_a[i] * vec_b[i] for i in range(length))
        norm_a = math.sqrt(sum(vec_a[i] * vec_a[i] for i in range(length)))
        norm_b = math.sqrt(sum(vec_b[i] * vec_b[i] for i in range(length)))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @log_execution
    def _embedding_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @log_execution
    def _load_embedding(self, record: PropertyEmbedding) -> List[float]:
        try:
            parsed = json.loads(record.embedding_data)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []

    @log_execution
    def _is_postgres(self) -> bool:
        try:
            return db.engine.dialect.name == "postgresql"
        except Exception:
            return False

    @log_execution
    def _has_pgvector_column(self) -> bool:
        if self._pgvector_column_available is not None:
            return self._pgvector_column_available

        if not self._is_postgres():
            self._pgvector_column_available = False
            return False

        try:
            row = db.session.execute(
                text(
                    """
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'property_embeddings'
                      AND column_name = 'embedding_vector'
                    LIMIT 1
                    """
                )
            ).first()
            self._pgvector_column_available = bool(row)
        except Exception as exc:
            self.logger.debug("Unable to inspect pgvector column: %s", exc)
            self._pgvector_column_available = False
        return self._pgvector_column_available

    @log_execution
    def _to_vector_literal(self, vector: List[float]) -> str:
        return "[" + ",".join(f"{float(v):.8f}" for v in vector) + "]"

    @log_execution
    def _store_pgvector_embedding(self, property_id: int, vector: List[float]) -> None:
        if not vector or not self._has_pgvector_column():
            return
        db.session.execute(
            text(
                """
                UPDATE property_embeddings
                SET embedding_vector = CAST(:vector_literal AS vector)
                WHERE property_id = :property_id
                """
            ),
            {
                "property_id": property_id,
                "vector_literal": self._to_vector_literal(vector),
            },
        )

    @log_execution
    def _pgvector_operator(self) -> str:
        if self.vector_distance in ("l2", "euclidean"):
            return "<->"
        if self.vector_distance in ("ip", "inner_product"):
            return "<#>"
        return "<=>"

    @log_execution
    def _distance_to_similarity(self, distance: float) -> float:
        if self.vector_distance in ("l2", "euclidean"):
            return 1.0 / (1.0 + max(0.0, distance))
        if self.vector_distance in ("ip", "inner_product"):
            # pgvector inner product operator returns negative inner product.
            return max(0.0, min(1.0, -distance))
        # cosine distance in pgvector is [0..2] for normalized vectors.
        return max(0.0, min(1.0, 1.0 - distance))

    @log_execution
    def _search_with_pgvector(
        self,
        customer_embedding: List[float],
        property_ids: List[int],
        top_k: int,
    ) -> Dict[int, float]:
        if not property_ids or not self._has_pgvector_column():
            return {}

        operator = self._pgvector_operator()
        query = (
            text(
                f"""
                SELECT property_id,
                       embedding_vector {operator} CAST(:query_vector AS vector) AS distance
                FROM property_embeddings
                WHERE embedding_vector IS NOT NULL
                  AND property_id IN :property_ids
                ORDER BY embedding_vector {operator} CAST(:query_vector AS vector)
                LIMIT :limit
                """
            )
            .bindparams(bindparam("property_ids", expanding=True))
        )

        rows = db.session.execute(
            query,
            {
                "query_vector": self._to_vector_literal(customer_embedding),
                "property_ids": property_ids,
                "limit": int(top_k),
            },
        ).all()

        scores: Dict[int, float] = {}
        for row in rows:
            pid = int(row[0])
            distance = float(row[1] or 0.0)
            scores[pid] = self._distance_to_similarity(distance)
        return scores

    @log_execution
    def index_properties(self, properties: List[Property]) -> bool:
        """Generate/update embeddings for the provided properties."""
        try:
            if not properties:
                return True

            texts: List[str] = []
            todo: List[Property] = []

            for prop in properties:
                if not prop.id:
                    continue
                if prop.is_deleted or prop.status != "active":
                    continue
                text_blob = self._create_property_text(prop)
                source_hash = self._embedding_hash(text_blob)
                existing = PropertyEmbedding.query.filter_by(property_id=prop.id).first()
                if existing and existing.source_hash == source_hash:
                    continue
                texts.append(text_blob)
                todo.append(prop)

            if not todo:
                return True

            vectors = embedding_provider.embed(texts)
            for prop, text_blob, vector in zip(todo, texts, vectors):
                source_hash = self._embedding_hash(text_blob)
                payload = json.dumps(vector)
                record = PropertyEmbedding.query.filter_by(property_id=prop.id).first()
                if not record:
                    record = PropertyEmbedding(
                        property_id=prop.id,
                        embedding_data=payload,
                        source_hash=source_hash,
                        provider=os.environ.get("EMBEDDING_PROVIDER", "gemini"),
                        dimension=len(vector) if vector else embedding_provider.dimension,
                    )
                    db.session.add(record)
                else:
                    record.embedding_data = payload
                    record.source_hash = source_hash
                    record.provider = os.environ.get("EMBEDDING_PROVIDER", "gemini")
                    record.dimension = len(vector) if vector else embedding_provider.dimension
                db.session.flush()
                self._store_pgvector_embedding(prop.id, vector)

            db.session.commit()
            self.logger.info("Indexed %s property embeddings", len(todo))
            return True
        except Exception as exc:
            db.session.rollback()
            self.logger.error("Error indexing properties: %s", exc)
            return False

    @log_execution
    def search_properties(
        self,
        customer: Customer,
        properties: List[Property],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Backward-compatible wrapper returning only ranked results."""
        result = self.search_properties_with_meta(customer=customer, properties=properties, top_k=top_k)
        return result.get("results", [])

    @log_execution
    def search_properties_with_meta(
        self,
        customer: Customer,
        properties: List[Property],
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """Find best matches and include deterministic degradation metadata."""
        try:
            if not properties:
                return {
                    "results": [],
                    "meta": {"mode": "empty", "is_fallback": True, "reason": "no_properties"},
                }
            properties = [p for p in properties if not p.is_deleted and p.status == "active"]
            if not properties:
                return {
                    "results": [],
                    "meta": {"mode": "empty", "is_fallback": True, "reason": "no_active_properties"},
                }

            neighborhood_benchmarks = build_neighborhood_price_per_sqm(properties)
            recent_favorites_map = build_recent_favorites_map(hours=48)
            customer_score = get_customer_score(customer)

            self.index_properties(properties)

            customer_text = self._create_customer_text(customer)
            customer_vectors = embedding_provider.embed([customer_text])
            customer_embedding = customer_vectors[0] if customer_vectors else []
            if not customer_embedding:
                return {
                    "results": self._fallback_search(
                        customer,
                        properties,
                        top_k,
                        neighborhood_benchmarks=neighborhood_benchmarks,
                        recent_favorites_map=recent_favorites_map,
                        customer_score=customer_score,
                    ),
                    "meta": {
                        "mode": "rule_fallback",
                        "is_fallback": True,
                        "reason": "missing_customer_embedding",
                        "customer_score": customer_score,
                    },
                }

            properties_by_id = {prop.id: prop for prop in properties if prop.id is not None}
            recommendations: List[Dict[str, Any]] = []

            # Use pgvector KNN on Postgres when available; otherwise use JSON fallback.
            pgvector_scores: Dict[int, float] = {}
            if self._has_pgvector_column():
                try:
                    pgvector_scores = self._search_with_pgvector(
                        customer_embedding=customer_embedding,
                        property_ids=list(properties_by_id.keys()),
                        top_k=max(top_k * 2, top_k),
                    )
                except Exception as exc:
                    self.logger.warning("pgvector query failed; using JSON similarity fallback: %s", exc)
                    pgvector_scores = {}

            if pgvector_scores:
                for property_id, similarity in pgvector_scores.items():
                    prop = properties_by_id.get(property_id)
                    if not prop:
                        continue
                    semantic_score = max(0.0, similarity) * 100.0
                    recommendations.append(
                        self._build_recommendation_item(
                            customer,
                            prop,
                            semantic_score,
                            customer_score=customer_score,
                            neighborhood_benchmarks=neighborhood_benchmarks,
                            recent_favorites_map=recent_favorites_map,
                        )
                    )
            else:
                missing_embeddings = False
                for prop in properties:
                    if not prop.id:
                        continue
                    record = PropertyEmbedding.query.filter_by(property_id=prop.id).first()
                    if not record:
                        missing_embeddings = True
                        continue
                    property_vector = self._load_embedding(record)
                    similarity = max(0.0, self._cosine_similarity(customer_embedding, property_vector))
                    semantic_score = similarity * 100.0
                    recommendations.append(
                        self._build_recommendation_item(
                            customer,
                            prop,
                            semantic_score,
                            customer_score=customer_score,
                            neighborhood_benchmarks=neighborhood_benchmarks,
                            recent_favorites_map=recent_favorites_map,
                        )
                    )

                if not recommendations and missing_embeddings:
                    return {
                        "results": self._fallback_search(
                            customer,
                            properties,
                            top_k,
                            neighborhood_benchmarks=neighborhood_benchmarks,
                            recent_favorites_map=recent_favorites_map,
                            customer_score=customer_score,
                        ),
                        "meta": {
                            "mode": "rule_fallback",
                            "is_fallback": True,
                            "reason": "missing_property_embeddings",
                            "customer_score": customer_score,
                        },
                    }

            recommendations.sort(
                key=lambda item: (
                    -item["hybrid_score"],
                    -float(getattr(item.get("property"), "rating", 0.0) or 0.0),
                    float(getattr(item.get("property"), "nightly_price", getattr(item.get("property"), "price", 0)) or 0),
                    int(getattr(item.get("property"), "id", 0) or 0),
                )
            )
            return {
                "results": recommendations[:top_k],
                "meta": {
                    "mode": "semantic_hybrid",
                    "is_fallback": False,
                    "reason": None,
                    "customer_score": customer_score,
                },
            }
        except Exception as exc:
            self.logger.error("Error in vector search: %s", exc)
            return {
                "results": self._fallback_search(customer, properties, top_k),
                "meta": {
                    "mode": "rule_fallback",
                    "is_fallback": True,
                    "reason": "vector_search_exception",
                },
            }

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            return int(value)
        except (TypeError, ValueError):
            return default

    def _score_budget(self, customer: Customer, property_obj: Property) -> float:
        """0–100 budget fit (sale price, rahn, or rent)."""
        price = property_obj.price if property_obj.price is not None else 0
        max_b = self._safe_int(customer.budget_max)
        min_b = self._safe_int(customer.budget_min)
        # Prefer sale price; for rentals also consider rahn within budget
        candidates = [price]
        if property_obj.rahn:
            candidates.append(int(property_obj.rahn))
        if property_obj.rental_price:
            candidates.append(int(property_obj.rental_price) * 12)  # rough annual

        best = 20.0
        for p in candidates:
            if max_b <= 0 and min_b <= 0:
                return 50.0  # no budget set → neutral
            if max_b > 0 and min_b > 0 and min_b <= p <= max_b:
                best = max(best, 100.0)
            elif max_b > 0 and p <= max_b * 1.1:
                best = max(best, 80.0)
            elif max_b > 0 and p <= max_b * 1.2:
                best = max(best, 60.0)
            elif min_b > 0 and p >= min_b * 0.5 and (max_b <= 0 or p <= max_b * 1.3):
                best = max(best, 40.0)
        return best

    def _score_location(self, customer: Customer, property_obj: Property) -> float:
        pref = (customer.location_preference or "").strip().lower()
        if not pref:
            return 50.0
        haystacks = [
            (property_obj.neighborhood or "").lower(),
            (property_obj.address or "").lower(),
            (property_obj.title or "").lower(),
        ]
        # Token overlap for multi-word prefs ("north tehran", "jordan")
        tokens = [t for t in pref.replace(",", " ").split() if len(t) > 1]
        if not tokens:
            return 50.0
        for hay in haystacks:
            if not hay:
                continue
            if pref in hay or hay in pref:
                return 100.0
            hits = sum(1 for t in tokens if t in hay)
            if hits == len(tokens):
                return 95.0
            if hits > 0:
                return 55.0 + 40.0 * (hits / len(tokens))
        return 15.0

    def _normalize_property_kind(self, text: str) -> str:
        """Map EN/FA listing labels to a coarse kind for matching."""
        t = (text or "").strip().lower()
        if not t:
            return ""
        # Persian labels common in this inventory
        if "آپارتمان" in t or "اپارتمان" in t:
            return "apartment"
        if "ویلا" in t or "ويلا" in t:
            return "villa"
        if "مغازه" in t or "تجاری" in t or "تجاري" in t:
            return "shop"
        if "زمین" in t or "زمين" in t:
            return "land"
        if "خانه" in t or "منزل" in t:
            return "house"
        # English / latin
        if any(k in t for k in ("apartment", "apt", "flat", "condo", "unit")):
            return "apartment"
        if "villa" in t:
            return "villa"
        if any(k in t for k in ("house", "home", "townhouse")):
            return "house"
        if any(k in t for k in ("land", "lot", "plot")):
            return "land"
        if any(k in t for k in ("shop", "store", "retail", "office", "commercial")):
            return "shop"
        return t

    def _score_type(self, customer: Customer, property_obj: Property) -> float:
        preferred_raw = (customer.preferred_type or "").strip().lower()
        actual_raw = (property_obj.property_type or "").strip().lower()
        if not preferred_raw:
            return 50.0
        if not actual_raw:
            return 30.0
        if preferred_raw == actual_raw:
            return 100.0

        preferred = self._normalize_property_kind(preferred_raw)
        actual = self._normalize_property_kind(actual_raw)
        if preferred and actual and preferred == actual:
            return 100.0

        # Related residential kinds
        residential = {"apartment", "villa", "house"}
        if preferred in residential and actual in residential:
            if {preferred, actual} == {"villa", "house"}:
                return 85.0
            return 55.0

        if preferred in actual_raw or actual_raw in preferred_raw or preferred in actual or actual in preferred:
            return 70.0
        return 15.0

    def _score_rooms(self, customer: Customer, property_obj: Property) -> float:
        score = 50.0
        parts = 0
        pref_beds = self._safe_int(customer.preferred_bedrooms)
        pref_baths = self._safe_int(customer.preferred_bathrooms)
        beds = self._safe_int(property_obj.bedrooms)
        baths = self._safe_int(property_obj.bathrooms)

        if pref_beds > 0:
            parts += 1
            diff = abs(beds - pref_beds)
            if diff == 0:
                bed_s = 100.0
            elif diff == 1:
                bed_s = 65.0
            elif diff == 2:
                bed_s = 35.0
            else:
                bed_s = 10.0
            score = bed_s if parts == 1 else (score + bed_s) / 2

        if pref_baths > 0:
            parts += 1
            diff = abs(baths - pref_baths)
            if baths >= pref_baths:
                bath_s = 100.0 if diff == 0 else 80.0
            elif diff == 1:
                bath_s = 50.0
            else:
                bath_s = 15.0
            if parts == 1:
                score = bath_s
            else:
                score = (score + bath_s) / 2

        return score if parts else 50.0

    def _preference_tokens(self, customer: Customer) -> List[str]:
        text = f"{customer.preferences or ''} {customer.location_preference or ''}"
        return [t.lower() for t in text.replace(",", " ").split() if len(t) > 2]

    def _score_amenities(self, customer: Customer, property_obj: Property) -> float:
        """Overlap between free-text prefs and property features / flags."""
        tokens = self._preference_tokens(customer)
        feature_blob = " ".join(
            [
                property_obj.property_features or "",
                property_obj.description or "",
                property_obj.heating_type or "",
                property_obj.cooling_type or "",
                "elevator" if property_obj.has_elevator else "",
                "storage" if property_obj.has_storage else "",
                "parking" if (property_obj.parking_spaces or 0) > 0 else "",
            ]
        ).lower()

        keyword_boosts = {
            "elevator": bool(property_obj.has_elevator),
            "parking": (property_obj.parking_spaces or 0) > 0,
            "storage": bool(property_obj.has_storage),
            "anbari": bool(property_obj.has_storage),
            "asansor": bool(property_obj.has_elevator),
        }

        if not tokens and not any(keyword_boosts.values()):
            return 50.0

        hits = 0
        checks = 0
        for t in tokens:
            checks += 1
            if t in feature_blob or keyword_boosts.get(t):
                hits += 1
        # Always reward explicit amenities when present even without prefs
        amenity_points = 0
        if property_obj.has_elevator:
            amenity_points += 15
        if (property_obj.parking_spaces or 0) > 0:
            amenity_points += 15
        if property_obj.has_storage:
            amenity_points += 10

        if checks == 0:
            return min(100.0, 40.0 + amenity_points)
        overlap = 100.0 * hits / checks
        return min(100.0, 0.7 * overlap + 0.3 * min(100.0, amenity_points * 2))

    def _score_size(self, customer: Customer, property_obj: Property) -> float:
        """Soft size fit from built_area / square_feet when prefs mention area numbers."""
        area = property_obj.built_area or property_obj.square_feet or 0
        if not area:
            return 50.0
        # Parse first number in preferences as approximate desired sqm/sqft
        prefs = customer.preferences or ""
        nums = re.findall(r"\b(\d{2,5})\b", prefs)
        if not nums:
            return 50.0
        target = int(nums[0])
        if target <= 0:
            return 50.0
        ratio = area / target
        if 0.85 <= ratio <= 1.15:
            return 100.0
        if 0.7 <= ratio <= 1.3:
            return 70.0
        if 0.5 <= ratio <= 1.5:
            return 40.0
        return 15.0

    @log_execution
    def score_breakdown(
        self,
        customer: Customer,
        property_obj: Property,
        semantic_score: float,
    ) -> Dict[str, float]:
        """Per-parameter scores 0–100 plus weighted total (hybrid)."""
        sem = max(0.0, min(100.0, float(semantic_score or 0.0)))
        # Without embeddings/API, semantic is often 0 and tanks hybrid to ~35%.
        # Use a neutral mid score and mark it so UI/debug can see it.
        semantic_missing = sem <= 0.01
        if semantic_missing:
            sem = 50.0

        components = {
            "semantic": sem,
            "budget": self._score_budget(customer, property_obj),
            "location": self._score_location(customer, property_obj),
            "type": self._score_type(customer, property_obj),
            "rooms": self._score_rooms(customer, property_obj),
            "amenities": self._score_amenities(customer, property_obj),
            "size": self._score_size(customer, property_obj),
        }
        weights = dict(self.weights)
        if semantic_missing:
            # Prefer rule weights when vector similarity is unavailable
            sem_w = weights.get("semantic", 0.0)
            weights["semantic"] = sem_w * 0.25
            boost = sem_w - weights["semantic"]
            for key in ("budget", "location", "type", "rooms"):
                weights[key] = weights.get(key, 0.0) + boost / 4.0
            total_w = sum(max(0.0, v) for v in weights.values()) or 1.0
            weights = {k: max(0.0, v) / total_w for k, v in weights.items()}

        hybrid = 0.0
        for key, value in components.items():
            hybrid += value * weights.get(key, 0.0)
        components["hybrid"] = min(100.0, max(0.0, hybrid))
        components["semantic_missing"] = 1.0 if semantic_missing else 0.0
        # Backward-compat alias used by older callers
        components["requirements"] = (components["type"] + components["rooms"]) / 2.0
        return components

    @log_execution
    def _calculate_hybrid_score(
        self,
        customer: Customer,
        property_obj: Property,
        semantic_score: float,
    ) -> float:
        return self.score_breakdown(customer, property_obj, semantic_score)["hybrid"]

    @log_execution
    def _generate_match_reasons(
        self,
        customer: Customer,
        property_obj: Property,
        similarity_score: float,
    ) -> List[str]:
        breakdown = self.score_breakdown(customer, property_obj, similarity_score)
        reasons: List[str] = []

        if breakdown["semantic"] > 70:
            reasons.append(f"High semantic match ({breakdown['semantic']:.0f}%)")
        elif breakdown["semantic"] > 50:
            reasons.append(f"Good semantic match ({breakdown['semantic']:.0f}%)")

        if breakdown["budget"] >= 100:
            reasons.append("Within budget")
        elif breakdown["budget"] >= 80:
            reasons.append("Near budget (+10%)")
        elif breakdown["budget"] >= 60:
            reasons.append("Slightly over budget")

        if breakdown["location"] >= 90:
            reasons.append("Matches location preference")
        elif breakdown["location"] >= 55:
            reasons.append("Partial location match")

        if breakdown["type"] >= 85:
            reasons.append("Matches property type")
        if breakdown["rooms"] >= 80:
            reasons.append("Fits bedroom/bath needs")
        elif breakdown["rooms"] >= 50 and self._safe_int(customer.preferred_bedrooms) > 0:
            reasons.append("Close on rooms")

        if breakdown["amenities"] >= 70:
            reasons.append("Amenity / feature overlap")
        if breakdown["size"] >= 85:
            reasons.append("Size fits preference")

        # Compact breakdown for agents/UI (always keep, even if we truncate other lines)
        mix = (
            f"Score mix: bud {breakdown['budget']:.0f} loc {breakdown['location']:.0f} "
            f"type {breakdown['type']:.0f} rooms {breakdown['rooms']:.0f}"
        )
        head = reasons[:5]
        return head + [mix]

    @log_execution
    def _fallback_search(
        self,
        customer: Customer,
        properties: List[Property],
        top_k: int,
        neighborhood_benchmarks: Optional[Dict[str, float]] = None,
        recent_favorites_map: Optional[Dict[int, int]] = None,
        customer_score: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if neighborhood_benchmarks is None:
            neighborhood_benchmarks = build_neighborhood_price_per_sqm(properties)
        if recent_favorites_map is None:
            recent_favorites_map = build_recent_favorites_map(hours=48)
        if customer_score is None:
            customer_score = get_customer_score(customer)

        recommendations: List[Dict[str, Any]] = []
        for prop in properties:
            recommendations.append(
                self._build_recommendation_item(
                    customer,
                    prop,
                    50.0,
                    customer_score=customer_score,
                    neighborhood_benchmarks=neighborhood_benchmarks,
                    recent_favorites_map=recent_favorites_map,
                )
            )
        recommendations.sort(key=lambda item: item["hybrid_score"], reverse=True)
        return recommendations[:top_k]

    def _build_recommendation_item(
        self,
        customer: Customer,
        prop: Property,
        semantic_score: float,
        customer_score: Optional[int] = None,
        neighborhood_benchmarks: Optional[Dict[str, float]] = None,
        recent_favorites_map: Optional[Dict[int, int]] = None,
    ) -> Dict[str, Any]:
        breakdown = self.score_breakdown(customer, prop, semantic_score)
        property_score = get_property_score(
            prop,
            neighborhood_benchmarks=neighborhood_benchmarks or {},
            recent_favorites_map=recent_favorites_map or {},
        )
        return {
            "property": prop,
            "semantic_score": semantic_score,
            "hybrid_score": breakdown["hybrid"],
            "score_breakdown": breakdown,
            "property_score": property_score,
            "customer_score": customer_score,
            "match_reasons": self._generate_match_reasons(customer, prop, semantic_score),
        }

    @log_execution
    def reset_database(self) -> None:
        try:
            PropertyEmbedding.query.delete()
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            self.logger.error("Error resetting embedding table: %s", exc)

    @log_execution
    def get_status(self) -> Dict[str, Any]:
        indexed = 0
        try:
            indexed = PropertyEmbedding.query.count()
        except Exception as exc:
            self.logger.debug("Unable to count property embeddings: %s", exc)

        return {
            "database_ready": indexed > 0,
            "properties_indexed": indexed,
            "customers_indexed": 0,
            "persist_directory": None,
            "provider": os.environ.get("EMBEDDING_PROVIDER", "gemini"),
            "vector_distance": self.vector_distance,
            "pgvector_enabled": self._has_pgvector_column(),
            # Backward-compat keys expected by existing route/UI.
            "vectorizer_fitted": indexed > 0,
            "vectorizer_file_exists": False,
        }


vector_service = VectorService()



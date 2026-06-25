import hashlib
import json
import logging
import math
import os
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

        # Hybrid weights (sum = 1.0) - configurable via environment variables
        semantic_weight = float(os.environ.get("SEMANTIC_WEIGHT", "0.60"))
        budget_weight = float(os.environ.get("BUDGET_WEIGHT", "0.25"))
        requirements_weight = float(os.environ.get("REQUIREMENTS_WEIGHT", "0.15"))
        total = semantic_weight + budget_weight + requirements_weight
        if total > 0:
            self.weights = {
                "semantic": semantic_weight / total,
                "budget": budget_weight / total,
                "requirements": requirements_weight / total,
            }
        else:
            self.weights = {
                "semantic": 0.60,
                "budget": 0.25,
                "requirements": 0.15,
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
                    hybrid_score = self._calculate_hybrid_score(customer, prop, semantic_score)
                    property_score = get_property_score(
                        prop,
                        neighborhood_benchmarks=neighborhood_benchmarks,
                        recent_favorites_map=recent_favorites_map,
                    )
                    recommendations.append(
                        {
                            "property": prop,
                            "semantic_score": semantic_score,
                            "hybrid_score": hybrid_score,
                            "property_score": property_score,
                            "customer_score": customer_score,
                            "match_reasons": self._generate_match_reasons(
                                customer,
                                prop,
                                semantic_score,
                            ),
                        }
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

                    hybrid_score = self._calculate_hybrid_score(customer, prop, semantic_score)
                    property_score = get_property_score(
                        prop,
                        neighborhood_benchmarks=neighborhood_benchmarks,
                        recent_favorites_map=recent_favorites_map,
                    )
                    recommendations.append(
                        {
                            "property": prop,
                            "semantic_score": semantic_score,
                            "hybrid_score": hybrid_score,
                            "property_score": property_score,
                            "customer_score": customer_score,
                            "match_reasons": self._generate_match_reasons(
                                customer,
                                prop,
                                semantic_score,
                            ),
                        }
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

    @log_execution
    def _calculate_hybrid_score(
        self,
        customer: Customer,
        property_obj: Property,
        semantic_score: float,
    ) -> float:
        semantic_component = semantic_score * self.weights.get("semantic", 0.60)

        budget_score = 0.0
        if customer.budget_min <= property_obj.price <= customer.budget_max:
            budget_score = 100
        elif customer.budget_max and property_obj.price <= customer.budget_max * 1.1:
            budget_score = 80
        elif customer.budget_max and property_obj.price <= customer.budget_max * 1.2:
            budget_score = 60
        else:
            budget_score = 20
        budget_component = budget_score * self.weights.get("budget", 0.25)

        requirements_score = 0.0
        if property_obj.bedrooms == customer.preferred_bedrooms:
            requirements_score += 40
        elif abs(property_obj.bedrooms - customer.preferred_bedrooms) <= 1:
            requirements_score += 20

        if property_obj.bathrooms >= customer.preferred_bathrooms:
            requirements_score += 30
        elif property_obj.bathrooms >= customer.preferred_bathrooms - 0.5:
            requirements_score += 15

        if (property_obj.property_type or "").lower() == (customer.preferred_type or "").lower():
            requirements_score += 30

        requirements_component = requirements_score * self.weights.get("requirements", 0.15)
        return min(100.0, max(0.0, semantic_component + budget_component + requirements_component))

    @log_execution
    def _generate_match_reasons(
        self,
        customer: Customer,
        property_obj: Property,
        similarity_score: float,
    ) -> List[str]:
        reasons: List[str] = []
        if similarity_score > 70:
            reasons.append(f"High semantic match ({similarity_score:.1f}%)")
        elif similarity_score > 50:
            reasons.append(f"Good semantic match ({similarity_score:.1f}%)")

        if customer.budget_min <= property_obj.price <= customer.budget_max:
            reasons.append("Within budget range")
        elif customer.budget_max and property_obj.price <= customer.budget_max * 1.1:
            reasons.append("Near budget range")

        if property_obj.bedrooms == customer.preferred_bedrooms:
            reasons.append("Matches bedroom preference")
        if property_obj.bathrooms >= customer.preferred_bathrooms:
            reasons.append("Meets bathroom requirements")
        if (property_obj.property_type or "").lower() == (customer.preferred_type or "").lower():
            reasons.append("Matches property type")

        return reasons[:4]

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
            score = self._calculate_hybrid_score(customer, prop, 50.0)
            property_score = get_property_score(
                prop,
                neighborhood_benchmarks=neighborhood_benchmarks,
                recent_favorites_map=recent_favorites_map,
            )
            recommendations.append(
                {
                    "property": prop,
                    "semantic_score": 50.0,
                    "hybrid_score": score,
                    "property_score": property_score,
                    "customer_score": customer_score,
                    "match_reasons": self._generate_match_reasons(customer, prop, 50.0),
                }
            )
        recommendations.sort(key=lambda item: item["hybrid_score"], reverse=True)
        return recommendations[:top_k]

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



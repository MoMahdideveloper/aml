import hashlib
import json
import logging
import os
import re
import time
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import has_app_context

from schemas import CustomerAI, PropertyAI
from sqlalchemy_models import Customer, Property
from services.llm import llm_provider
from services.llm.providers.kie_provider import KieProvider
from services.ai_model_analytics_service import record_gemini_reasoning_operation, record_property_recommendation_operation
from utils.execution_tracer import log_execution


class GeminiService:
    """
    Gemini-first service facade.
    Uses provider abstractions and keeps deterministic fallbacks when provider is unavailable.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("services.gemini_service")
        self.provider = llm_provider
        self.reasoning_top_n = int(os.environ.get("RECOMMENDATION_REASONING_TOP_N", "3"))
        self.reasoning_cache_ttl_seconds = int(os.environ.get("GEMINI_REASONING_CACHE_TTL_SECONDS", "1800"))
        self.reasoning_cache_version = os.environ.get("GEMINI_REASONING_CACHE_VERSION", "1")
        self._reasoning_cache: Dict[str, Dict[str, Any]] = {}
        # Image cache for extract_property_from_image
        self._image_cache: Dict[str, Dict[str, Any]] = {}
        self._image_cache_ttl_seconds = int(os.environ.get("GEMINI_IMAGE_CACHE_TTL_SECONDS", "3600"))
        self._last_recommendation_meta: Dict[str, Any] = {
            "is_fallback": False,
            "reason": None,
            "search_mode": "unknown",
        }

    @log_execution
    def _set_recommendation_meta(self, **kwargs: Any) -> None:
        self._last_recommendation_meta = {
            "is_fallback": bool(kwargs.get("is_fallback", False)),
            "reason": kwargs.get("reason"),
            "search_mode": kwargs.get("search_mode", "unknown"),
            "message": kwargs.get("message"),
        }

    @log_execution
    def get_last_recommendation_meta(self) -> Dict[str, Any]:
        return dict(self._last_recommendation_meta)

    @log_execution
    def _cache_get(self, key: str) -> Any:
        if has_app_context():
            try:
                from extensions import cache

                return cache.get(key)
            except Exception as exc:
                self.logger.debug("Gemini cache get failed for %s: %s", key, exc)
        return self._reasoning_cache.get(key)

    @log_execution
    def _cache_set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        if has_app_context():
            try:
                from extensions import cache

                cache.set(key, value, timeout=timeout or self.reasoning_cache_ttl_seconds)
                return
            except Exception as exc:
                self.logger.debug("Gemini cache set failed for %s: %s", key, exc)
        self._reasoning_cache[key] = value

    @log_execution
    def _cache_version_key(self, entity_type: str, entity_id: int) -> str:
        return f"gemini_reasoning:v{self.reasoning_cache_version}:version:{entity_type}:{entity_id}"

    @log_execution
    def _get_entity_cache_version(self, entity_type: str, entity_id: Optional[int]) -> int:
        if not entity_id:
            return 1
        key = self._cache_version_key(entity_type, int(entity_id))
        version = self._cache_get(key)
        return int(version or 1)

    @log_execution
    def bump_entity_cache_version(self, entity_type: str, entity_id: int) -> None:
        if not entity_id:
            return
        key = self._cache_version_key(entity_type, int(entity_id))
        current_version = self._get_entity_cache_version(entity_type, entity_id)
        self._cache_set(key, current_version + 1, timeout=86400 * 365)

    @log_execution
    def _reasoning_cache_key(
        self,
        customer: Customer,
        property_obj: Property,
        reasons: List[str],
        score: float,
    ) -> str:
        payload = {
            "customer_id": customer.id,
            "property_id": property_obj.id,
            "customer_pref": {
                "budget_min": customer.budget_min,
                "budget_max": customer.budget_max,
                "preferred_type": customer.preferred_type,
                "preferred_bedrooms": customer.preferred_bedrooms,
                "preferred_bathrooms": customer.preferred_bathrooms,
                "location": customer.location_preference,
            },
            "property": {
                "price": property_obj.price,
                "type": property_obj.property_type,
                "bedrooms": property_obj.bedrooms,
                "bathrooms": property_obj.bathrooms,
                "neighborhood": property_obj.neighborhood,
                "updated_at": property_obj.updated_at.isoformat() if property_obj.updated_at else None,
            },
            "reasons": reasons,
            "score": round(score, 2),
            "customer_version": self._get_entity_cache_version("customer", customer.id),
            "property_version": self._get_entity_cache_version("property", property_obj.id),
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        return f"gemini_reasoning:v{self.reasoning_cache_version}:{digest}"

    @log_execution
    def _fallback_reasoning(self, score: float, reasons: List[str]) -> Dict[str, Any]:
        return {
            "explanation": f"This property has a match score of {score:.1f}/100 based on your preferences.",
            "pros": reasons,
            "cons": [],
        }

    @log_execution
    def _generate_reasoning(
        self,
        customer: Customer,
        property_obj: Property,
        reasons: List[str],
        score: float,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        import time
        start_time = time.time()

        # Create a cache key that includes conversation history if provided
        cache_key = self._reasoning_cache_key(customer, property_obj, reasons, score)
        if conversation_history:
            # Add a hash of the conversation history to the cache key to differentiate
            history_str = json.dumps(conversation_history, sort_keys=True)
            history_hash = hashlib.sha256(history_str.encode("utf-8")).hexdigest()[:16]
            cache_key = f"{cache_key}:{history_hash}"

        # Check cache first
        cached = self._cache_get(cache_key)
        if cached:
            # Record cache hit
            latency_ms = (time.time() - start_time) * 1000
            record_gemini_reasoning_operation(
                customer_id=customer.id if customer else None,
                property_id=property_obj.id if property_obj else None,
                latency_ms=latency_ms,
                success=True,
                conversation_history_length=len(conversation_history) if conversation_history else 0,
                reasoning_type="cached"
            )
            return cached

        if not self.provider.is_available:
            data = self._fallback_reasoning(score, reasons)
            self._cache_set(cache_key, data)
            latency_ms = (time.time() - start_time) * 1000
            record_gemini_reasoning_operation(
                customer_id=customer.id if customer else None,
                property_id=property_obj.id if property_obj else None,
                latency_ms=latency_ms,
                success=True,
                conversation_history_length=len(conversation_history) if conversation_history else 0,
                reasoning_type="fallback"
            )
            return data

        # Prepare payload for provider, including conversation history if available
        payload = {
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "budget_min": customer.budget_min,
                "budget_max": customer.budget_max,
                "preferred_type": customer.preferred_type,
                "preferred_bedrooms": customer.preferred_bedrooms,
                "preferred_bathrooms": customer.preferred_bathrooms,
                "location": customer.location_preference,
            },
            "property": {
                "id": property_obj.id,
                "title": property_obj.title,
                "price": property_obj.price,
                "type": property_obj.property_type,
                "bedrooms": property_obj.bedrooms,
                "bathrooms": property_obj.bathrooms,
                "neighborhood": property_obj.neighborhood,
                "square_feet": property_obj.square_feet,
                "year_built": property_obj.year_built,
                "description": property_obj.description,
            },
            "reasons": reasons,
            "score": round(score, 2),
            "conversation_history": conversation_history or [],
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()
        # Use the same cache key structure for consistency
        cache_key = f"gemini_reasoning:v{self.reasoning_cache_version}:{digest}"
        if conversation_history:
            # Add conversation history hash to cache key for provider-based results too
            history_str = json.dumps(conversation_history, sort_keys=True)
            history_hash = hashlib.sha256(history_str.encode("utf-8")).hexdigest()[:16]
            cache_key = f"{cache_key}:{history_hash}"

        data = self.provider.generate_recommendation_reasoning(
            customer=customer,
            property_obj=property_obj,
            reasons=reasons,
            score=score,
            conversation_history=conversation_history,
        )
        if not data:
            data = self._fallback_reasoning(score, reasons)

        self._cache_set(cache_key, data)
        latency_ms = (time.time() - start_time) * 1000
        record_gemini_reasoning_operation(
            customer_id=customer.id if customer else None,
            property_id=property_obj.id if property_obj else None,
            latency_ms=latency_ms,
            success=bool(data),
            conversation_history_length=len(conversation_history) if conversation_history else 0,
            reasoning_type="provider" if data else "fallback"
        )
        return data

    @log_execution
    def get_property_recommendations(
        self,
        customer: Customer,
        properties: List[Property],
    ) -> List[Dict[str, Any]]:
        """Get ranked property recommendations with limited-cost reasoning generation."""
        import time
        start_time = time.time()

        try:
            from services.search_service import search_service

            if hasattr(search_service, "search_properties_with_meta"):
                ranked_bundle = search_service.search_properties_with_meta(customer=customer, top_k=10)
                ranked = ranked_bundle.get("results", []) if isinstance(ranked_bundle, dict) else []
                search_meta = ranked_bundle.get("meta", {}) if isinstance(ranked_bundle, dict) else {}
            else:
                ranked = search_service.search_properties(customer=customer, top_k=10)
                search_meta = {"mode": "legacy", "is_fallback": False}

            if not ranked:
                self._set_recommendation_meta(
                    is_fallback=True,
                    reason=(search_meta.get("fallback_reason") if isinstance(search_meta, dict) else None) or "no_ranked_results",
                    search_mode=(search_meta.get("mode") if isinstance(search_meta, dict) else None) or "keyword_only",
                    message="AI ranking unavailable. Showing deterministic fallback recommendations.",
                )
                latency_ms = (time.time() - start_time) * 1000
                record_property_recommendation_operation(
                    customer_id=customer.id if customer else None,
                    properties_count=len(properties[:10]) if properties else 0,
                    latency_ms=latency_ms,
                    success=False,  # Failed to get rankings
                    has_conversation_history=False
                )
                return self._create_fallback_recommendations(customer, properties[:10])

            formatted: List[Dict[str, Any]] = []
            for idx, rec in enumerate(ranked):
                property_obj = rec["property"]
                reasons = rec.get("match_reasons", [])
                hybrid_score = float(rec.get("hybrid_score", 0))

                if idx < self.reasoning_top_n:
                    analysis_data = self._generate_reasoning(customer, property_obj, reasons, hybrid_score)
                else:
                    analysis_data = self._fallback_reasoning(hybrid_score, reasons)

                breakdown = rec.get("score_breakdown") or {}
                if not breakdown and property_obj is not None:
                    try:
                        from services.vector_service import vector_service

                        breakdown = vector_service.score_breakdown(
                            customer,
                            property_obj,
                            float(rec.get("semantic_score") or 50.0),
                        )
                    except Exception:
                        breakdown = {}

                formatted.append(
                    {
                        "property": property_obj,
                        "analysis": analysis_data.get("explanation", ""),
                        "pros": analysis_data.get("pros", []),
                        "cons": analysis_data.get("cons", []),
                        "match_score": int(round(hybrid_score)),
                        "match_reasons": reasons,
                        "score_breakdown": breakdown,
                        "hybrid_breakdown": {
                            "semantic": rec.get("semantic_score", 0)
                            or (breakdown.get("semantic") if breakdown else 0),
                            "keyword": rec.get("keyword_score", 0),
                            **{
                                k: breakdown.get(k)
                                for k in (
                                    "budget",
                                    "location",
                                    "type",
                                    "rooms",
                                    "amenities",
                                    "size",
                                    "hybrid",
                                )
                                if breakdown
                            },
                        },
                    }
                )

            is_fallback = bool(search_meta.get("is_fallback", False)) if isinstance(search_meta, dict) else False
            fallback_reason = search_meta.get("fallback_reason") if isinstance(search_meta, dict) else None
            self._set_recommendation_meta(
                is_fallback=is_fallback,
                reason=fallback_reason,
                search_mode=(search_meta.get("mode") if isinstance(search_meta, dict) else None) or "hybrid",
                message=(
                    "AI ranking degraded. Showing deterministic fallback recommendations."
                    if is_fallback
                    else None
                ),
            )

            latency_ms = (time.time() - start_time) * 1000
            record_property_recommendation_operation(
                customer_id=customer.id if customer else None,
                properties_count=len(formatted),
                latency_ms=latency_ms,
                success=not is_fallback,  # Success if not using fallback
                has_conversation_history=False  # This method doesn't use conversation history
            )
            return formatted
        except Exception as exc:
            self.logger.error(f"Error generating recommendations: {exc}")
            self._set_recommendation_meta(
                is_fallback=True,
                reason="gemini_service_exception",
                search_mode="keyword_only",
                message="AI service temporarily unavailable. Showing basic recommendations.",
            )
            latency_ms = (time.time() - start_time) * 1000
            record_property_recommendation_operation(
                customer_id=customer.id if customer else None,
                properties_count=len(properties[:10]) if properties else 0,
                latency_ms=latency_ms,
                success=False,  # Exception occurred
                has_conversation_history=False
            )
            return self._create_fallback_recommendations(customer, properties[:10])

    @log_execution
    def get_context_aware_property_recommendations(
        self,
        customer: Customer,
        properties: List[Property],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Get ranked property recommendations with context-aware reasoning generation.

        This method extends get_property_recommendations by incorporating conversation history
        into the reasoning generation process for more contextual recommendations.
        """
        import time
        start_time = time.time()

        try:
            from services.search_service import search_service

            if hasattr(search_service, "search_properties_with_meta"):
                ranked_bundle = search_service.search_properties_with_meta(customer=customer, top_k=10)
                ranked = ranked_bundle.get("results", []) if isinstance(ranked_bundle, dict) else []
                search_meta = ranked_bundle.get("meta", {}) if isinstance(ranked_bundle, dict) else {}
            else:
                ranked = search_service.search_properties(customer=customer, top_k=10)
                search_meta = {"mode": "legacy", "is_fallback": False}

            if not ranked:
                self._set_recommendation_meta(
                    is_fallback=True,
                    reason=(search_meta.get("fallback_reason") if isinstance(search_meta, dict) else None) or "no_ranked_results",
                    search_mode=(search_meta.get("mode") if isinstance(search_meta, dict) else None) or "keyword_only",
                    message="AI ranking unavailable. Showing deterministic fallback recommendations.",
                )
                latency_ms = (time.time() - start_time) * 1000
                record_property_recommendation_operation(
                    customer_id=customer.id if customer else None,
                    properties_count=len(properties[:10]) if properties else 0,
                    latency_ms=latency_ms,
                    success=False,  # Failed to get rankings
                    has_conversation_history=bool(conversation_history and len(conversation_history) > 0)
                )
                return self._create_fallback_recommendations(customer, properties[:10])

            formatted: List[Dict[str, Any]] = []
            for idx, rec in enumerate(ranked):
                property_obj = rec["property"]
                reasons = rec.get("match_reasons", [])
                hybrid_score = float(rec.get("hybrid_score", 0))

                if idx < self.reasoning_top_n:
                    # Pass conversation history to _generate_reasoning for context-aware reasoning
                    analysis_data = self._generate_reasoning(
                        customer=customer,
                        property_obj=property_obj,
                        reasons=reasons,
                        score=hybrid_score,
                        conversation_history=conversation_history,
                    )
                else:
                    analysis_data = self._fallback_reasoning(hybrid_score, reasons)

                breakdown = rec.get("score_breakdown") or {}
                if not breakdown and property_obj is not None:
                    try:
                        from services.vector_service import vector_service

                        breakdown = vector_service.score_breakdown(
                            customer,
                            property_obj,
                            float(rec.get("semantic_score") or 50.0),
                        )
                    except Exception:
                        breakdown = {}

                formatted.append(
                    {
                        "property": property_obj,
                        "analysis": analysis_data.get("explanation", ""),
                        "pros": analysis_data.get("pros", []),
                        "cons": analysis_data.get("cons", []),
                        "match_score": int(round(hybrid_score)),
                        "match_reasons": reasons,
                        "score_breakdown": breakdown,
                        "hybrid_breakdown": {
                            "semantic": rec.get("semantic_score", 0)
                            or (breakdown.get("semantic") if breakdown else 0),
                            "keyword": rec.get("keyword_score", 0),
                            **{
                                k: breakdown.get(k)
                                for k in (
                                    "budget",
                                    "location",
                                    "type",
                                    "rooms",
                                    "amenities",
                                    "size",
                                    "hybrid",
                                )
                                if breakdown
                            },
                        },
                    }
                )

            is_fallback = bool(search_meta.get("is_fallback", False)) if isinstance(search_meta, dict) else False
            fallback_reason = search_meta.get("fallback_reason") if isinstance(search_meta, dict) else None
            self._set_recommendation_meta(
                is_fallback=is_fallback,
                reason=fallback_reason,
                search_mode=(search_meta.get("mode") if isinstance(search_meta, dict) else None) or "hybrid",
                message=(
                    "AI ranking degraded. Showing deterministic fallback recommendations."
                    if is_fallback
                    else None
                ),
            )

            latency_ms = (time.time() - start_time) * 1000
            record_property_recommendation_operation(
                customer_id=customer.id if customer else None,
                properties_count=len(formatted),
                latency_ms=latency_ms,
                success=not is_fallback,  # Success if not using fallback
                has_conversation_history=bool(conversation_history and len(conversation_history) > 0)
            )
            return formatted
        except Exception as exc:
            self.logger.error(f"Error generating context-aware recommendations: {exc}")
            self._set_recommendation_meta(
                is_fallback=True,
                reason="gemini_service_exception",
                search_mode="keyword_only",
                message="AI service temporarily unavailable. Showing basic recommendations.",
            )
            latency_ms = (time.time() - start_time) * 1000
            record_property_recommendation_operation(
                customer_id=customer.id if customer else None,
                properties_count=len(properties[:10]) if properties else 0,
                latency_ms=latency_ms,
                success=False,  # Exception occurred
                has_conversation_history=bool(conversation_history and len(conversation_history) > 0)
            )
            return self._create_fallback_recommendations(customer, properties[:10])

    @log_execution
    def _create_fallback_recommendations(
        self,
        customer: Customer,
        properties: List[Property],
    ) -> List[Dict[str, Any]]:
        recommendations: List[Dict[str, Any]] = []

        for prop in properties:
            score = 0
            reasons: List[str] = []

            if customer.budget_min <= prop.price <= customer.budget_max:
                score += 40
                reasons.append("Within budget range")
            elif customer.budget_max and prop.price <= customer.budget_max:
                score += 20
                reasons.append("Slightly below budget")

            if prop.bedrooms == customer.preferred_bedrooms:
                score += 20
                reasons.append("Matches bedroom preference")
            elif abs(prop.bedrooms - customer.preferred_bedrooms) <= 1:
                score += 10
                reasons.append("Close to bedroom preference")

            if prop.bathrooms >= customer.preferred_bathrooms:
                score += 20
                reasons.append("Meets bathroom needs")
            elif prop.bathrooms >= customer.preferred_bathrooms - 0.5:
                score += 10
                reasons.append("Close to bathroom preference")

            if (prop.property_type or "").lower() == (customer.preferred_type or "").lower():
                score += 20
                reasons.append("Matches property type preference")

            analysis = f"Match Score: {score}/100\n" + "\n".join(f"- {reason}" for reason in reasons)
            if not reasons:
                analysis = "This property may not fully match your preferences, but could still be worth considering."

            recommendations.append(
                {
                    "property": prop,
                    "analysis": analysis,
                    "pros": reasons,
                    "cons": [],
                    "match_score": score,
                }
            )

        recommendations.sort(
            key=lambda item: (
                -float(item.get("match_score", 0) or 0),
                -float(getattr(item.get("property"), "rating", 0.0) or 0.0),
                float(getattr(item.get("property"), "nightly_price", getattr(item.get("property"), "price", 0)) or 0),
                int(getattr(item.get("property"), "id", 0) or 0),
            )
        )
        return recommendations

    @log_execution
    def generate_market_analysis(self, stats: Dict[str, Any], properties: List[Property]) -> Dict[str, Any]:
        total = stats.get("total_properties", len(properties or []))
        active = stats.get("active_properties", 0)
        avg_price = stats.get("avg_property_price", 0)

        neighborhoods = [getattr(p, "neighborhood", None) for p in properties or []]
        neighborhoods = [n for n in neighborhoods if n]
        top = ", ".join(f"{name} ({cnt})" for name, cnt in Counter(neighborhoods).most_common(3))

        fallback_analysis = (
            f"Market snapshot: {total} properties ({active} active). "
            f"Average price ${avg_price:,.0f}."
        )
        fallback_bullets = [
            f"Listings: {total} total, {active} active",
            f"Average price: ${avg_price:,.0f}",
            f"Top neighborhoods: {top or 'N/A'}",
        ]

        if not self.provider.is_available:
            return {"analysis": fallback_analysis, "bullets": fallback_bullets}

        prompt = (
            "Return concise market analysis for real estate agents.\n"
            f"Total properties: {total}\n"
            f"Active properties: {active}\n"
            f"Average price: {avg_price:,.0f}\n"
            f"Top neighborhoods: {top or 'N/A'}\n"
            "Format:\nOverview: <one sentence>\n- <bullet 1>\n- <bullet 2>\n- <bullet 3>"
        )
        text = self.provider.generate_market_analysis(prompt)
        if not text:
            return {"analysis": fallback_analysis, "bullets": fallback_bullets}

        overview = ""
        bullets: List[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.lower().startswith("overview:"):
                overview = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- "):
                bullets.append(stripped[2:].strip())

        return {
            "analysis": overview or fallback_analysis,
            "bullets": bullets or fallback_bullets,
        }

    @log_execution
    def extract_property_from_text(self, blob: str) -> Dict[str, Any]:
        data = self.provider.extract_property(blob) if self.provider.is_available else {}
        try:
            model = PropertyAI(**(data or {}))
            payload = model.model_dump() if hasattr(model, "model_dump") else model.dict()
            missing = [k for k, v in payload.items() if v in (None, [], "")]
            return {
                "entity": "property",
                "data": payload,
                "missing": missing,
                "confidence": 0.75 if data else 0.3,
            }
        except Exception as exc:
            self.logger.error(f"Property extraction failed: {exc}")
            return {"entity": "property", "data": {}, "missing": [], "confidence": 0.0}

    @log_execution
    def extract_customer_from_text(self, blob: str) -> Dict[str, Any]:
        data = self.provider.extract_customer(blob) if self.provider.is_available else {}
        try:
            model = CustomerAI(**(data or {}))
            payload = model.model_dump() if hasattr(model, "model_dump") else model.dict()
            missing = [k for k, v in payload.items() if v in (None, [], "")]
            return {
                "entity": "customer",
                "data": payload,
                "missing": missing,
                "confidence": 0.75 if data else 0.3,
            }
        except Exception as exc:
            self.logger.error(f"Customer extraction failed: {exc}")
            return {"entity": "customer", "data": {}, "missing": [], "confidence": 0.0}

    @log_execution
    def extract_property_from_image(self, image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        """Extract property details from an image (flyer/screenshot) with caching."""
        # Create a cache key based on image bytes hash and mime type
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        cache_key = f"image:{image_hash}:{mime_type}"

        # Check cache with TTL
        now = time.time()
        if cache_key in self._image_cache:
            cached_entry = self._image_cache[cache_key]
            if now - cached_entry["timestamp"] < self._image_cache_ttl_seconds:
                self.logger.debug(f"Image cache hit for key {cache_key[:16]}...")
                return cached_entry["data"]
            else:
                # Expired, remove it
                del self._image_cache[cache_key]

        # If not in cache or expired, proceed
        if not self.provider.is_available:
            return {}
        # Only GeminiProvider has this method currently
        if hasattr(self.provider, "extract_property_from_image"):
            result = self.provider.extract_property_from_image(image_bytes, mime_type)
            # Store in cache with timestamp
            self._image_cache[cache_key] = {
                "data": result,
                "timestamp": now
            }
            return result
        return {}

    @log_execution
    def generate_property_description(self, property_data: Dict[str, Any]) -> str:
        # Keep existing endpoint behavior with deterministic fallback.
        return property_data.get("description", "")

    @log_execution
    def analyze_market_trends(self, properties: List[Property]) -> str:
        stats = {
            "total_properties": len(properties),
            "active_properties": len([p for p in properties if p.status == "active"]),
            "avg_property_price": (
                sum(p.price for p in properties if p.price) / max(1, len([p for p in properties if p.price]))
            ),
        }
        result = self.generate_market_analysis(stats, properties)
        bullets = "\n".join(f"- {b}" for b in result.get("bullets", []))
        return f"{result.get('analysis', '')}\n{bullets}".strip()

    @log_execution
    def generate_matchmaker_pitch(
        self,
        customer: Customer,
        property_obj: Property,
        match_score: int,
        customer_score: int,
        property_score: int,
        smart_benefits: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Generate an outreach SMS draft with deterministic fallback."""
        benefit_text = ""
        if isinstance(smart_benefits, list) and smart_benefits:
            first = smart_benefits[0]
            if isinstance(first, dict):
                benefit_text = str(first.get("benefit") or "").strip()
            elif isinstance(first, str):
                benefit_text = first.strip()
        if not benefit_text:
            benefit_text = "This listing lines up well with your current preferences."

        fallback = (
            f"Hi {customer.name}. I found {property_obj.title} as a {match_score}% match. "
            f"{benefit_text} Are you free this week for a tour?"
        )

        if not self.provider.is_available:
            return fallback

        try:
            prompt = (
                "Write one concise SMS for a real-estate agent.\n"
                "Keep it natural, direct, and under 320 characters.\n"
                f"Customer name: {customer.name}\n"
                f"Customer score: {customer_score}\n"
                f"Property title: {property_obj.title}\n"
                f"Property address: {property_obj.address}\n"
                f"Property score: {property_score}\n"
                f"Match score: {match_score}\n"
                f"Benefit: {benefit_text}\n"
            )
            text = self.provider.generate_market_analysis(prompt)
            text = (text or "").strip()
            return text if text else fallback
        except Exception as exc:
            self.logger.warning("Matchmaker pitch generation failed; using fallback: %s", exc)
            return fallback


# Global service instance expected by routes

gemini_service = GeminiService()

_RAG_LOGGER = logging.getLogger("services.gemini_service")
_COPILOT_KIE_PROVIDER: Optional[KieProvider] = None


@log_execution
def _safe_int(value: Any) -> Optional[int]:
    try:
        if value in (None, ""):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


@log_execution
def _normalize_history(conversation_history: Any, max_items: int = 20) -> List[Dict[str, Any]]:
    if not isinstance(conversation_history, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for item in conversation_history[-max_items:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "").lower()
        if role not in {"user", "model", "assistant"}:
            continue
        if role == "assistant":
            role = "model"

        parts_raw = item.get("parts", [])
        if isinstance(parts_raw, str):
            parts_raw = [parts_raw]

        parts: List[Dict[str, str]] = []
        if isinstance(parts_raw, list):
            for part in parts_raw:
                if isinstance(part, dict):
                    text = str(part.get("text") or "").strip()
                    if text:
                        parts.append({"text": text})
                else:
                    text = str(part or "").strip()
                    if text:
                        parts.append({"text": text})
        if parts:
            normalized.append({"role": role, "parts": parts})
    return normalized


@log_execution
def _get_copilot_provider():
    """Copilot should prefer KIE when configured; otherwise use configured default provider."""
    global _COPILOT_KIE_PROVIDER
    if _COPILOT_KIE_PROVIDER is None:
        try:
            _COPILOT_KIE_PROVIDER = KieProvider()
        except Exception as exc:
            _RAG_LOGGER.warning("Failed to initialize KIE provider for copilot: %s", exc)
            _COPILOT_KIE_PROVIDER = None

    if _COPILOT_KIE_PROVIDER and _COPILOT_KIE_PROVIDER.is_available:
        return _COPILOT_KIE_PROVIDER
    return llm_provider


@log_execution
def _provider_text_completion(prompt: str) -> str:
    provider = _get_copilot_provider()
    if not provider or not provider.is_available:
        return ""
    try:
        # Reusing provider text generation contract keeps copilot provider-agnostic.
        text = provider.generate_market_analysis(prompt)
    except Exception as exc:
        _RAG_LOGGER.warning("Copilot provider completion failed: %s", exc)
        return ""
    return (text or "").strip()


@log_execution
def _extract_json_dict(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


@log_execution
def _history_to_text(normalized_history: List[Dict[str, Any]], max_items: int = 8) -> str:
    if not normalized_history:
        return "No previous context."

    lines: List[str] = []
    for item in normalized_history[-max_items:]:
        role = str(item.get("role") or "user")
        parts = item.get("parts") or []
        texts: List[str] = []
        if isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict):
                    txt = str(part.get("text") or "").strip()
                    if txt:
                        texts.append(txt)
                else:
                    txt = str(part or "").strip()
                    if txt:
                        texts.append(txt)
        if texts:
            lines.append(f"{role}: {' '.join(texts)}")
    return "\n".join(lines) if lines else "No previous context."


@log_execution
def _extract_first_int(text: str, patterns: List[str]) -> Optional[int]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        number = match.group(1).replace(",", "")
        parsed = _safe_int(number)
        if parsed is not None:
            return parsed
    return None


@log_execution
def _extract_location_hint(text: str) -> Optional[str]:
    match = re.search(r"\bin\s+([a-zA-Z][a-zA-Z\s\-]{2,40})", text, flags=re.IGNORECASE)
    if not match:
        return None
    raw = " ".join(match.group(1).split())
    noise = {"the", "a", "an", "my", "your", "this", "that", "property", "properties", "customer", "customers"}
    if raw.lower() in noise:
        return None
    return raw


@log_execution
def _infer_property_type(text: str) -> Optional[str]:
    lowered = text.lower()
    for token in ("apartment", "condo", "villa", "house", "office", "commercial"):
        if token in lowered:
            return token
    return None


@log_execution
def _infer_intent_type(text: str) -> Optional[str]:
    lowered = text.lower()
    if "hot lead" in lowered or "urgent" in lowered:
        return "hot"
    if "investor" in lowered or "investment" in lowered:
        return "investor"
    if "first time" in lowered or "first-time" in lowered:
        return "first_time_buyer"
    return None


@log_execution
def _extract_enum_hint(text: str, choices: List[str]) -> Optional[str]:
    lowered = text.lower()
    for choice in choices:
        if choice.lower() in lowered:
            return choice
    return None


@log_execution
def _extract_due_date_hint(text: str, direction: str) -> Optional[str]:
    pattern = (
        r"(?:before|until|due before)\s*(\d{4}-\d{2}-\d{2})"
        if direction == "before"
        else r"(?:after|from|due after)\s*(\d{4}-\d{2}-\d{2})"
    )
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1)


@log_execution
def _infer_search_domain(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("task", "tasks", "todo", "to-do")):
        return "tasks"
    if any(token in lowered for token in ("deal", "deals", "pipeline", "offer")):
        return "deals"
    if any(token in lowered for token in ("agent", "agents", "broker")):
        return "agents"
    if any(token in lowered for token in ("customer", "customers", "lead", "leads", "buyer", "buyers")):
        return "customers"
    return "properties"


@log_execution
def _summarize_property_results(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "I couldn't find matching active properties for those filters. Please try relaxing the constraints."

    lines = [f"I found {len(results)} matching active properties:"]
    for idx, item in enumerate(results[:5], start=1):
        title = item.get("title") or f"Property #{item.get('id')}"
        bedrooms = item.get("bedrooms")
        square_feet = item.get("square_feet")
        price = _safe_int(item.get("price")) or 0
        neighborhood = item.get("neighborhood") or "N/A"
        lines.append(
            f"{idx}. {title} | {bedrooms} bed | {square_feet} sqm | ${price:,.0f} | {neighborhood}"
        )
    lines.append("Tell me if you want tighter filters (price, area, type, or location).")
    return "\n".join(lines)


@log_execution
def _summarize_customer_results(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "I couldn't find matching active customers for those constraints."

    lines = [f"I found {len(results)} matching customers/leads:"]
    for idx, item in enumerate(results[:5], start=1):
        name = item.get("name") or f"Customer #{item.get('id')}"
        budget_min = _safe_int(item.get("budget_min")) or 0
        budget_max = _safe_int(item.get("budget_max")) or 0
        beds = item.get("preferred_bedrooms")
        location = item.get("location_preference") or "N/A"
        priority_hint = item.get("priority_hint") or "normal"
        lines.append(
            f"{idx}. {name} | budget ${budget_min:,.0f}-${budget_max:,.0f} | {beds}+ beds | {location} | priority {priority_hint}"
        )
    lines.append("I can also match these leads directly to inventory if you want.")
    return "\n".join(lines)


@log_execution
def _summarize_deal_results(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "I couldn't find deals matching those filters."

    lines = [f"I found {len(results)} matching deals:"]
    for idx, item in enumerate(results[:5], start=1):
        deal_id = item.get("id")
        status = item.get("status") or "unknown"
        offer = _safe_int(item.get("offer_amount")) or 0
        customer = item.get("customer_name") or "N/A"
        property_title = item.get("property_title") or "N/A"
        agent = item.get("agent_name") or "Unassigned"
        lines.append(
            f"{idx}. Deal #{deal_id} | {status} | ${offer:,.0f} | {customer} | {property_title} | Agent: {agent}"
        )
    lines.append("Add filters like status, offer range, customer, property, or agent for narrower results.")
    return "\n".join(lines)


@log_execution
def _summarize_task_results(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "I couldn't find tasks matching those filters."

    lines = [f"I found {len(results)} matching tasks:"]
    for idx, item in enumerate(results[:5], start=1):
        title = item.get("title") or f"Task #{item.get('id')}"
        status = item.get("status") or "unknown"
        priority = item.get("priority") or "normal"
        due = item.get("due_date") or "No due date"
        agent = item.get("agent_name") or "N/A"
        lines.append(f"{idx}. {title} | {status} | {priority} | due: {due} | Agent: {agent}")
    lines.append("Try filters like priority, status, due-before/after, agent, or keyword.")
    return "\n".join(lines)


@log_execution
def _summarize_agent_results(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "I couldn't find agents matching those filters."

    lines = [f"I found {len(results)} matching agents:"]
    for idx, item in enumerate(results[:5], start=1):
        name = item.get("name") or f"Agent #{item.get('id')}"
        specialization = item.get("specialization") or "N/A"
        sales = _safe_int(item.get("total_sales")) or 0
        listings = _safe_int(item.get("active_listings")) or 0
        lines.append(f"{idx}. {name} | {specialization} | sales: {sales} | active listings: {listings}")
    lines.append("You can filter by specialization, sales, active listings, or keyword.")
    return "\n".join(lines)


@log_execution
def _run_local_query_fallback(user_prompt: str) -> str:
    from services.search_service import (
        execute_agent_search,
        execute_customer_search,
        execute_deal_search,
        execute_property_search,
        execute_task_search,
    )

    text = user_prompt or ""
    domain = _infer_search_domain(text)
    lowered = text.lower()

    min_beds = _extract_first_int(text, [r"(\d+)\s*(?:bed|beds|bedroom|bedrooms)"])
    min_sqm = _extract_first_int(
        text,
        [
            r"(?:over|above|more than|at least|>=)\s*(\d+)\s*(?:sqm|sq ?m|m2|meter|meters|square ?feet|sqft)",
            r"(\d+)\s*(?:sqm|sq ?m|m2|meter|meters|square ?feet|sqft)",
        ],
    )
    min_price = _extract_first_int(text, [r"(?:above|over|at least|>=)\s*\$?\s*([\d,]+)\s*(?:usd|dollars)?"])
    max_price = _extract_first_int(text, [r"(?:below|under|less than|<=)\s*\$?\s*([\d,]+)\s*(?:usd|dollars)?"])
    location = _extract_location_hint(text)
    keyword_match = re.search(r"(?:keyword|contains)\s+([a-zA-Z0-9 _-]{2,80})", text, flags=re.IGNORECASE)
    keyword = keyword_match.group(1).strip() if keyword_match else None
    agent_name_match = re.search(r"(?:agent|by)\s+([a-zA-Z][a-zA-Z\s\-]{1,60})", text, flags=re.IGNORECASE)
    agent_name = agent_name_match.group(1).strip() if agent_name_match else None

    if domain == "customers":
        customers = execute_customer_search(
            intent_type=_infer_intent_type(text),
            min_budget=min_price,
            max_budget=max_price,
            preferred_beds=min_beds,
            location=location,
            top_k=5,
        )
        return _summarize_customer_results(customers)

    if domain == "deals":
        deal_status = _extract_enum_hint(
            lowered,
            ["prospecting", "qualified", "negotiation", "closed_won", "closed_lost", "won", "lost"],
        )
        min_offer = _extract_first_int(
            text,
            [r"(?:offer|amount)\s*(?:over|above|at least|>=)\s*\$?\s*([\d,]+)", r"(?:over|above)\s*\$?\s*([\d,]+)"],
        )
        max_offer = _extract_first_int(
            text,
            [r"(?:offer|amount)\s*(?:under|below|less than|<=)\s*\$?\s*([\d,]+)", r"(?:under|below)\s*\$?\s*([\d,]+)"],
        )
        customer_name_match = re.search(r"(?:customer|buyer)\s+([a-zA-Z][a-zA-Z\s\-]{1,60})", text, flags=re.IGNORECASE)
        customer_name = customer_name_match.group(1).strip() if customer_name_match else None
        property_name_match = re.search(r"(?:property|listing)\s+([a-zA-Z0-9][a-zA-Z0-9\s\-]{1,80})", text, flags=re.IGNORECASE)
        property_title = property_name_match.group(1).strip() if property_name_match else None
        deals = execute_deal_search(
            status=deal_status,
            min_offer=min_offer,
            max_offer=max_offer,
            customer_name=customer_name,
            property_title=property_title,
            agent_name=agent_name,
            keyword=keyword,
            top_k=5,
        )
        return _summarize_deal_results(deals)

    if domain == "tasks":
        task_status = _extract_enum_hint(
            lowered,
            ["pending", "in_progress", "completed", "cancelled", "on_hold", "overdue"],
        )
        task_priority = _extract_enum_hint(
            lowered,
            ["low", "medium", "high", "urgent"],
        )
        due_before = _extract_due_date_hint(text, "before")
        due_after = _extract_due_date_hint(text, "after")
        tasks = execute_task_search(
            status=task_status,
            priority=task_priority,
            agent_name=agent_name,
            due_before=due_before,
            due_after=due_after,
            keyword=keyword,
            top_k=5,
        )
        return _summarize_task_results(tasks)

    if domain == "agents":
        specialization_match = re.search(r"(?:specialization|specialty|specialized in)\s+([a-zA-Z][a-zA-Z\s\-]{1,60})", text, flags=re.IGNORECASE)
        specialization = specialization_match.group(1).strip() if specialization_match else None
        min_sales = _extract_first_int(
            text,
            [r"(?:sales|total sales)\s*(?:over|above|at least|>=)\s*([\d,]+)"],
        )
        min_listings = _extract_first_int(
            text,
            [r"(?:listings|active listings)\s*(?:over|above|at least|>=)\s*([\d,]+)"],
        )
        agents = execute_agent_search(
            name=agent_name if "agent " in lowered else None,
            specialization=specialization,
            min_total_sales=min_sales,
            min_active_listings=min_listings,
            keyword=keyword,
            top_k=5,
        )
        return _summarize_agent_results(agents)

    properties = execute_property_search(
        beds=min_beds,
        sqm=min_sqm,
        min_price=min_price,
        max_price=max_price,
        property_type=_infer_property_type(text),
        location=location,
        top_k=5,
    )
    return _summarize_property_results(properties)


@log_execution
def chat_with_agentic_rag(user_prompt: str, conversation_history: Any) -> str:
    """Agentic chat using provider-routed tool planning with deterministic SQL fallback."""
    prompt = (user_prompt or "").strip()
    if not prompt:
        return "Please enter a question so I can search properties, customers, deals, tasks, or agents."

    normalized_history = _normalize_history(conversation_history)

    try:
        routing_prompt = (
            "You are a real-estate copilot router. Return ONLY valid JSON with this schema:\n"
            "{\n"
            '  "call": "search_properties" | "search_customers" | "search_deals" | "search_tasks" | "search_agents" | "none",\n'
            '  "args": {\n'
            '    "keyword": string|null,\n'
            '    "min_beds": integer|null,\n'
            '    "min_sqm": integer|null,\n'
            '    "min_price": integer|null,\n'
            '    "max_price": integer|null,\n'
            '    "property_type": string|null,\n'
            '    "location": string|null,\n'
            '    "listing_type": string|null,\n'
            '    "min_parking": integer|null,\n'
            '    "min_floors": integer|null,\n'
            '    "has_elevator": boolean|null,\n'
            '    "has_storage": boolean|null,\n'
            '    "document_type": string|null,\n'
            '    "floor_covering": string|null,\n'
            '    "facade_type": string|null,\n'
            '    "heating_type": string|null,\n'
            '    "cooling_type": string|null,\n'
            '    "property_direction": string|null,\n'
            '    "min_land_area": integer|null,\n'
            '    "min_year_built": integer|null,\n'
            '    "property_category": string|null,\n'
            '    "is_exchangeable": boolean|null,\n'
            '    "file_code": string|null,\n'
            '    "max_rahn": integer|null,\n'
            '    "max_ejare": integer|null,\n'
            '    "top_k": integer|null,\n'
            '    "intent_type": string|null,\n'
            '    "min_budget": integer|null,\n'
            '    "max_budget": integer|null,\n'
            '    "preferred_beds": integer|null,\n'
            '    "deal_status": string|null,\n'
            '    "min_offer": integer|null,\n'
            '    "max_offer": integer|null,\n'
            '    "customer_name": string|null,\n'
            '    "property_title": string|null,\n'
            '    "agent_name": string|null,\n'
            '    "task_status": string|null,\n'
            '    "task_priority": string|null,\n'
            '    "due_before": string|null,\n'
            '    "due_after": string|null,\n'
            '    "specialization": string|null,\n'
            '    "min_total_sales": integer|null,\n'
            '    "min_active_listings": integer|null\n'
            "  },\n"
            '  "reply": string\n'
            "}\n"
            "Rules:\n"
            "- Use search_properties for listing filters, property names, or amenity queries.\n"
            "- Put property names/titles like 'باغ ویلا' in keyword, NOT in property_type.\n"
            "- Use search_customers for lead/customer queries.\n"
            "- Use search_deals for pipeline/deal/offer queries.\n"
            "- Use search_tasks for task/todo queries.\n"
            "- Use search_agents for agent/team performance queries.\n"
            "- Use call=none only for generic questions not requiring DB data.\n"
            "- If unsure, choose the most specific search call (not none).\n\n"
            f"Conversation history:\n{_history_to_text(normalized_history)}\n\n"
            f"User message:\n{prompt}"
        )

        # ─── Try native function calling first ───────────────────────────
        fc_result = _try_function_calling(prompt, normalized_history)
        if fc_result is not None:
            return fc_result

        # ─── Legacy JSON-prompt fallback ──────────────────────────────────
        routing_text = _provider_text_completion(routing_prompt)
        routing_json = _extract_json_dict(routing_text)

        call = str(routing_json.get("call") or "").strip().lower()
        args = routing_json.get("args") if isinstance(routing_json.get("args"), dict) else {}
        reply_from_router = str(routing_json.get("reply") or "").strip()

        from services.search_service import (
            execute_agent_search,
            execute_customer_search,
            execute_deal_search,
            execute_property_search,
            execute_task_search,
        )

        if call == "search_properties":
            tool_results = execute_property_search(
                beds=_safe_int(args.get("min_beds")),
                sqm=_safe_int(args.get("min_sqm")),
                min_price=_safe_int(args.get("min_price")),
                max_price=_safe_int(args.get("max_price")),
                property_type=args.get("property_type"),
                location=args.get("location"),
                keyword=args.get("keyword"),
                listing_type=args.get("listing_type"),
                min_parking=_safe_int(args.get("min_parking")),
                min_floors=_safe_int(args.get("min_floors")),
                has_elevator=args.get("has_elevator"),
                has_storage=args.get("has_storage"),
                document_type=args.get("document_type"),
                floor_covering=args.get("floor_covering"),
                facade_type=args.get("facade_type"),
                heating_type=args.get("heating_type"),
                cooling_type=args.get("cooling_type"),
                property_direction=args.get("property_direction"),
                min_land_area=_safe_int(args.get("min_land_area")),
                min_year_built=_safe_int(args.get("min_year_built")),
                property_category=args.get("property_category"),
                is_exchangeable=args.get("is_exchangeable"),
                file_code=args.get("file_code"),
                max_rahn=_safe_int(args.get("max_rahn")),
                max_ejare=_safe_int(args.get("max_ejare")),
                top_k=_safe_int(args.get("top_k")) or 5,
            )
            deterministic_summary = _summarize_property_results(tool_results)
            tool_name = "search_properties"
        elif call == "search_customers":
            tool_results = execute_customer_search(
                intent_type=args.get("intent_type"),
                min_budget=_safe_int(args.get("min_budget")),
                max_budget=_safe_int(args.get("max_budget")),
                preferred_beds=_safe_int(args.get("preferred_beds")),
                location=args.get("location"),
                top_k=_safe_int(args.get("top_k")) or 5,
            )
            deterministic_summary = _summarize_customer_results(tool_results)
            tool_name = "search_customers"
        elif call == "search_deals":
            tool_results = execute_deal_search(
                status=args.get("deal_status"),
                min_offer=_safe_int(args.get("min_offer")),
                max_offer=_safe_int(args.get("max_offer")),
                customer_name=args.get("customer_name"),
                property_title=args.get("property_title"),
                agent_name=args.get("agent_name"),
                keyword=args.get("keyword"),
                top_k=_safe_int(args.get("top_k")) or 5,
            )
            deterministic_summary = _summarize_deal_results(tool_results)
            tool_name = "search_deals"
        elif call == "search_tasks":
            tool_results = execute_task_search(
                status=args.get("task_status"),
                priority=args.get("task_priority"),
                agent_name=args.get("agent_name"),
                due_before=args.get("due_before"),
                due_after=args.get("due_after"),
                keyword=args.get("keyword"),
                top_k=_safe_int(args.get("top_k")) or 5,
            )
            deterministic_summary = _summarize_task_results(tool_results)
            tool_name = "search_tasks"
        elif call == "search_agents":
            tool_results = execute_agent_search(
                name=args.get("agent_name"),
                specialization=args.get("specialization"),
                min_total_sales=_safe_int(args.get("min_total_sales")),
                min_active_listings=_safe_int(args.get("min_active_listings")),
                keyword=args.get("keyword"),
                top_k=_safe_int(args.get("top_k")) or 5,
            )
            deterministic_summary = _summarize_agent_results(tool_results)
            tool_name = "search_agents"
        else:
            # No valid tool call from provider; prefer provider reply if present, else local deterministic routing.
            if reply_from_router:
                return reply_from_router
            return _run_local_query_fallback(prompt)

        synthesis_prompt = (
            "You are an assistant for real-estate agents. Use the tool result data below to answer clearly.\n"
            "Keep answers concise and practical. Mention counts and top matches.\n"
            "If no results, suggest relaxing constraints.\n\n"
            f"User message: {prompt}\n"
            f"Tool: {tool_name}\n"
            f"Args: {json.dumps(args, ensure_ascii=False)}\n"
            f"Results: {json.dumps(tool_results, ensure_ascii=False)}\n"
        )
        synthesized = _provider_text_completion(synthesis_prompt)
        return synthesized or deterministic_summary
    except Exception as exc:
        _RAG_LOGGER.warning("[RAG Fallback] Copilot provider route failed, using deterministic search: %s", exc)
        return _run_local_query_fallback(prompt)


# ── Native Function Calling (OpenAI-compatible tools) ──────────────────────

COPILOT_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_properties",
            "description": "Search the property listings database. Use for any query about properties, apartments, houses, villas, offices, prices, bedrooms, area, neighborhood, listing filters, amenities, or property names/titles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "Free-text search across property title, description, address, and features. Use for property names like 'باغ ویلا' or feature descriptions like 'نوساز'"},
                    "min_beds": {"type": "integer", "description": "Minimum number of bedrooms"},
                    "min_sqm": {"type": "integer", "description": "Minimum area in square meters"},
                    "min_price": {"type": "integer", "description": "Minimum price in toman"},
                    "max_price": {"type": "integer", "description": "Maximum price in toman"},
                    "property_type": {"type": "string", "description": "Property type filter, e.g. apartment, house, villa, office, commercial"},
                    "location": {"type": "string", "description": "Neighborhood, city name, or address"},
                    "listing_type": {"type": "string", "description": "Listing type: 'sale' or 'rental'"},
                    "min_parking": {"type": "integer", "description": "Minimum number of parking spaces"},
                    "min_floors": {"type": "integer", "description": "Minimum number of floors in the building"},
                    "has_elevator": {"type": "boolean", "description": "Filter for properties with elevator (آسانسور)"},
                    "has_storage": {"type": "boolean", "description": "Filter for properties with storage room (انباری)"},
                    "document_type": {"type": "string", "description": "Document type, e.g. سندی, منقوله, وکالتی"},
                    "floor_covering": {"type": "string", "description": "Floor covering type, e.g. سرامیک, پارکت, سنگ"},
                    "facade_type": {"type": "string", "description": "Facade material, e.g. سنگ, آجر, کامپوزیت"},
                    "heating_type": {"type": "string", "description": "Heating type, e.g. شوفاژ, پکیج, موتورخانه"},
                    "cooling_type": {"type": "string", "description": "Cooling type, e.g. کولر, اسپلیت, چیلر"},
                    "property_direction": {"type": "string", "description": "Property direction: north, south, east, west (شمالی, جنوبی, شرقی, غربی)"},
                    "min_land_area": {"type": "integer", "description": "Minimum land/lot area in square meters"},
                    "min_year_built": {"type": "integer", "description": "Minimum year built (e.g. 1400 for solar calendar)"},
                    "property_category": {"type": "string", "description": "Category: residential, commercial, industrial"},
                    "is_exchangeable": {"type": "boolean", "description": "Filter for properties available for exchange (معاوضه)"},
                    "file_code": {"type": "string", "description": "Unique listing/file code number"},
                    "max_rahn": {"type": "integer", "description": "Maximum deposit amount in toman (for rentals)"},
                    "max_ejare": {"type": "integer", "description": "Maximum monthly rent in toman (for rentals)"},
                    "top_k": {"type": "integer", "description": "Max results to return (default 5)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_customers",
            "description": "Search the customer/lead database. Use for any query about buyers, customers, leads, their budgets, or preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent_type": {"type": "string", "description": "Customer intent: hot, investor, first_time_buyer"},
                    "min_budget": {"type": "integer", "description": "Minimum budget in toman"},
                    "max_budget": {"type": "integer", "description": "Maximum budget in toman"},
                    "preferred_beds": {"type": "integer", "description": "Preferred number of bedrooms"},
                    "location": {"type": "string", "description": "Preferred location/neighborhood"},
                    "top_k": {"type": "integer", "description": "Max results to return (default 5)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_deals",
            "description": "Search the deals/pipeline database. Use for any query about deals, offers, pipeline status, negotiations, or closed transactions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "deal_status": {"type": "string", "description": "Deal status: prospecting, qualified, negotiation, closed_won, closed_lost"},
                    "min_offer": {"type": "integer", "description": "Minimum offer amount"},
                    "max_offer": {"type": "integer", "description": "Maximum offer amount"},
                    "customer_name": {"type": "string", "description": "Filter by customer name"},
                    "property_title": {"type": "string", "description": "Filter by property title"},
                    "agent_name": {"type": "string", "description": "Filter by agent name"},
                    "keyword": {"type": "string", "description": "Free-text keyword filter"},
                    "top_k": {"type": "integer", "description": "Max results to return (default 5)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_tasks",
            "description": "Search the tasks/to-do database. Use for any query about tasks, to-dos, follow-ups, deadlines, or agent workload.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_status": {"type": "string", "description": "Task status: pending, in_progress, completed, cancelled, on_hold, overdue"},
                    "task_priority": {"type": "string", "description": "Task priority: low, medium, high, urgent"},
                    "agent_name": {"type": "string", "description": "Filter by assigned agent name"},
                    "due_before": {"type": "string", "description": "Due date upper bound (YYYY-MM-DD)"},
                    "due_after": {"type": "string", "description": "Due date lower bound (YYYY-MM-DD)"},
                    "keyword": {"type": "string", "description": "Free-text keyword filter"},
                    "top_k": {"type": "integer", "description": "Max results to return (default 5)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_agents",
            "description": "Search the agents/team database. Use for any query about agents, brokers, team performance, sales numbers, or specializations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Agent name to search for"},
                    "specialization": {"type": "string", "description": "Agent specialization, e.g. Residential, Commercial, Luxury"},
                    "min_total_sales": {"type": "integer", "description": "Minimum total sales count"},
                    "min_active_listings": {"type": "integer", "description": "Minimum active listings count"},
                    "keyword": {"type": "string", "description": "Free-text keyword filter"},
                    "top_k": {"type": "integer", "description": "Max results to return (default 5)"},
                },
                "required": [],
            },
        },
    },
]

_COPILOT_SYSTEM_PROMPT = (
    "You are a helpful real-estate CRM copilot for Iranian agents. "
    "You can search properties, customers, deals, tasks, and agents. "
    "Use the provided tools when the user asks about data in the CRM. "
    "For general questions (greetings, how-to, advice), respond directly without tools. "
    "Keep answers concise, practical, and in the same language the user writes in."
)


@log_execution
def _extract_tool_calls(response_body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract tool_calls from an OpenAI-compatible chat completions response."""
    choices = response_body.get("choices")
    if not isinstance(choices, list) or not choices:
        return []
    first = choices[0]
    if not isinstance(first, dict):
        return []
    message = first.get("message")
    if not isinstance(message, dict):
        return []
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    return tool_calls


@log_execution
def _extract_text_reply(response_body: Dict[str, Any]) -> str:
    """Extract plain text reply from an OpenAI-compatible response (no tool calls)."""
    choices = response_body.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    # Handle list-form content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or ""
                if text:
                    parts.append(str(text).strip())
            elif isinstance(item, str):
                parts.append(item.strip())
        return "\n".join(p for p in parts if p)
    return ""


@log_execution
def _execute_tool_call(function_name: str, arguments: Dict[str, Any]) -> tuple:
    """Execute a copilot tool call and return (tool_name, results_list, summary_text)."""
    from services.search_service import (
        execute_agent_search,
        execute_customer_search,
        execute_deal_search,
        execute_property_search,
        execute_task_search,
    )

    top_k = _safe_int(arguments.get("top_k")) or 5

    if function_name == "search_properties":
        results = execute_property_search(
            beds=_safe_int(arguments.get("min_beds")),
            sqm=_safe_int(arguments.get("min_sqm")),
            min_price=_safe_int(arguments.get("min_price")),
            max_price=_safe_int(arguments.get("max_price")),
            property_type=arguments.get("property_type"),
            location=arguments.get("location"),
            keyword=arguments.get("keyword"),
            listing_type=arguments.get("listing_type"),
            min_parking=_safe_int(arguments.get("min_parking")),
            min_floors=_safe_int(arguments.get("min_floors")),
            has_elevator=arguments.get("has_elevator"),
            has_storage=arguments.get("has_storage"),
            document_type=arguments.get("document_type"),
            floor_covering=arguments.get("floor_covering"),
            facade_type=arguments.get("facade_type"),
            heating_type=arguments.get("heating_type"),
            cooling_type=arguments.get("cooling_type"),
            property_direction=arguments.get("property_direction"),
            min_land_area=_safe_int(arguments.get("min_land_area")),
            min_year_built=_safe_int(arguments.get("min_year_built")),
            property_category=arguments.get("property_category"),
            is_exchangeable=arguments.get("is_exchangeable"),
            file_code=arguments.get("file_code"),
            max_rahn=_safe_int(arguments.get("max_rahn")),
            max_ejare=_safe_int(arguments.get("max_ejare")),
            top_k=top_k,
        )
        return function_name, results, _summarize_property_results(results)

    if function_name == "search_customers":
        results = execute_customer_search(
            intent_type=arguments.get("intent_type"),
            min_budget=_safe_int(arguments.get("min_budget")),
            max_budget=_safe_int(arguments.get("max_budget")),
            preferred_beds=_safe_int(arguments.get("preferred_beds")),
            location=arguments.get("location"),
            top_k=top_k,
        )
        return function_name, results, _summarize_customer_results(results)

    if function_name == "search_deals":
        results = execute_deal_search(
            status=arguments.get("deal_status"),
            min_offer=_safe_int(arguments.get("min_offer")),
            max_offer=_safe_int(arguments.get("max_offer")),
            customer_name=arguments.get("customer_name"),
            property_title=arguments.get("property_title"),
            agent_name=arguments.get("agent_name"),
            keyword=arguments.get("keyword"),
            top_k=top_k,
        )
        return function_name, results, _summarize_deal_results(results)

    if function_name == "search_tasks":
        results = execute_task_search(
            status=arguments.get("task_status"),
            priority=arguments.get("task_priority"),
            agent_name=arguments.get("agent_name"),
            due_before=arguments.get("due_before"),
            due_after=arguments.get("due_after"),
            keyword=arguments.get("keyword"),
            top_k=top_k,
        )
        return function_name, results, _summarize_task_results(results)

    if function_name == "search_agents":
        results = execute_agent_search(
            name=arguments.get("agent_name"),
            specialization=arguments.get("specialization"),
            min_total_sales=_safe_int(arguments.get("min_total_sales")),
            min_active_listings=_safe_int(arguments.get("min_active_listings")),
            keyword=arguments.get("keyword"),
            top_k=top_k,
        )
        return function_name, results, _summarize_agent_results(results)

    return function_name, [], "Unknown tool."


@log_execution
def _try_function_calling(user_prompt: str, normalized_history: List[Dict[str, Any]]) -> Optional[str]:
    """Attempt native function calling via the provider. Returns None if not supported."""
    provider = _get_copilot_provider()
    if not provider or not provider.is_available:
        return None

    # Only KieProvider (and similar) supports _chat_completion_with_tools
    if not hasattr(provider, "_chat_completion_with_tools"):
        return None

    # Build messages array
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": _COPILOT_SYSTEM_PROMPT},
    ]
    # Add conversation history
    for item in normalized_history[-8:]:
        role = item.get("role", "user")
        parts = item.get("parts", [])
        text_parts = []
        for part in parts:
            if isinstance(part, dict):
                t = part.get("text", "")
                if t:
                    text_parts.append(t)
            elif isinstance(part, str) and part:
                text_parts.append(part)
        if text_parts:
            messages.append({"role": role, "content": " ".join(text_parts)})

    messages.append({"role": "user", "content": user_prompt})

    # First LLM call: ask with tool definitions
    try:
        response_body = provider._chat_completion_with_tools(messages, COPILOT_TOOL_DEFINITIONS)
    except Exception as exc:
        _RAG_LOGGER.warning("[Function Calling] Provider tools call failed: %s", exc)
        return None

    if not response_body:
        return None

    tool_calls = _extract_tool_calls(response_body)

    # No tool calls → model wants to reply directly
    if not tool_calls:
        text_reply = _extract_text_reply(response_body)
        if text_reply:
            _RAG_LOGGER.info("[Function Calling] Direct reply (no tool call)")
            return text_reply
        return None  # fall through to legacy

    # Execute the first tool call
    first_tc = tool_calls[0]
    if not isinstance(first_tc, dict):
        return None
    func_info = first_tc.get("function") or {}
    if not isinstance(func_info, dict):
        return None
    function_name = str(func_info.get("name") or "").strip()
    raw_args = func_info.get("arguments", "{}")
    # Arguments may be a JSON string or already parsed dict
    if isinstance(raw_args, str):
        try:
            arguments = json.loads(raw_args)
        except Exception:
            arguments = {}
    elif isinstance(raw_args, dict):
        arguments = raw_args
    else:
        arguments = {}

    if not function_name:
        return None

    _RAG_LOGGER.info("[Function Calling] Tool: %s | Args: %s", function_name, json.dumps(arguments, ensure_ascii=False))

    try:
        tool_name, tool_results, deterministic_summary = _execute_tool_call(function_name, arguments)
    except Exception as exc:
        _RAG_LOGGER.warning("[Function Calling] Tool execution failed: %s", exc)
        return None

    # Second LLM call: send tool results back for natural-language synthesis
    tool_call_id = first_tc.get("id") or "call_1"
    synthesis_messages = messages + [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [first_tc],
        },
        {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(tool_results, ensure_ascii=False),
        },
    ]
    try:
        synth_response = provider._chat_completion_with_tools(synthesis_messages)
        synth_text = _extract_text_reply(synth_response) if synth_response else ""
    except Exception as exc:
        _RAG_LOGGER.warning("[Function Calling] Synthesis call failed: %s", exc)
        synth_text = ""

    return synth_text or deterministic_summary

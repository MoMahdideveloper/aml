"""
Application service for recommendation use-case.
"""

from typing import List, Optional

from sqlalchemy_models import Customer, Property
from database import db
from services.gemini_service import gemini_service
from application.dtos import RecommendationRequest, RecommendationResult
from application.result import Success


class RecommendationService:
    """Application service for generating property recommendations."""

    def __init__(self):
        self.db_session = db.session

    def get_recommendations(self, request: RecommendationRequest) -> List[RecommendationResult]:
        """
        Get property recommendations for a customer.

        Args:
            request: RecommendationRequest containing customer_id and limit

        Returns:
            List of RecommendationResult
        """
        # Get the customer
        customer = db.session.get(Customer, request.customer_id)
        if not customer:
            return []

        # Get active properties (we can adjust the query as needed)
        properties = db.session.query(Property).filter(Property.is_deleted.is_(False), Property.status == "active").all()

        # Get recommendations from the Gemini service
        raw_recommendations = gemini_service.get_property_recommendations(customer, properties)

        # Convert to RecommendationResult objects and limit to the requested number
        results: List[RecommendationResult] = []
        for idx, raw in enumerate(raw_recommendations):
            if idx >= request.limit:
                break
            prop = raw.get("property")
            if not prop:
                continue

            result = RecommendationResult(
                property_id=prop.id,
                match_score=raw.get("match_score", 0),
                analysis=raw.get("analysis", ""),
                pros=raw.get("pros", []),
                cons=raw.get("cons", []),
                hybrid_breakdown=raw.get("hybrid_breakdown", {}),
            )
            results.append(result)

        return results
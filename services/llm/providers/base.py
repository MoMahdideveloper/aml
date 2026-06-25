from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from sqlalchemy_models import Customer, Property


class LLMProvider(ABC):
    """Provider interface for recommendation reasoning and extraction features."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate_recommendation_reasoning(
        self,
        customer: Customer,
        property_obj: Property,
        reasons: List[str],
        score: float,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def extract_property(self, blob: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def extract_customer(self, blob: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_market_analysis(self, prompt: str) -> str:
        raise NotImplementedError

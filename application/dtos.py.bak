from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class SearchRequest:
    query: Optional[str] = None
    listing_type: Optional[str] = None
    status: Optional[str] = None
    property_type: Optional[str] = None
    property_category: Optional[str] = None
    property_condition: Optional[str] = None
    neighborhood: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    min_sqft: Optional[int] = None
    max_sqft: Optional[int] = None
    year_built_min: Optional[int] = None
    year_built_max: Optional[int] = None
    agent_id: Optional[int] = None
    source: Optional[str] = None
    page: int = 1
    per_page: int = 20


@dataclass
class RecommendationRequest:
    customer_id: int
    limit: int = 10


@dataclass
class RecommendationResult:
    property_id: int
    match_score: int
    analysis: str
    pros: List[str]
    cons: List[str]
    hybrid_breakdown: Dict[str, Any]

@dataclass
class PropertyMatchInput:
    property_id: str
    embedding: List[float]
    metadata: Dict[str, Any]

@dataclass
class RecommendationContext:
    customer_id: str
    property_ids: List[str]
    preferences: Dict[str, Any]
    timestamp: datetime

@dataclass
class SyncBatchResult:
    success_count: int
    failure_count: int
    errors: List[str]
    synced_at: datetime

@dataclass
class EnvironmentUpdateRequest:
    key: str
    value: str
    description: Optional[str] = None

@dataclass
class WebhookSignaturePayload:
    timestamp: str
    signature: str
    payload: str
from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from datetime import datetime

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

@dataclass(frozen=True)
class RentalTerms:
    rahn: Optional[Money] = None  # deposit
    ejare: Optional[Money] = None  # monthly rent
    duration_months: Optional[int] = None

@dataclass(frozen=True)
class SyncCursor:
    provider: str
    last_synced: datetime
    cursor_id: Optional[str] = None

@dataclass(frozen=True)
class MatchScore:
    score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    factors: dict[str, float]

@dataclass(frozen=True)
class ProviderResultMetadata:
    provider: str
    request_id: str
    response_time_ms: int
    raw_response: Optional[dict] = None
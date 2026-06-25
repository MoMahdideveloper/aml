from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RecommendationResult:
    """Canonical recommendation payload shared across providers/services."""
    explanation: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

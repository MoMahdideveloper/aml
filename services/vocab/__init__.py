"""CRM vocabulary: normalize, synonym expand, directional replacements (query-only)."""

from services.vocab.expand import expand_query_terms, MAX_EXPANDED_KEYS
from services.vocab.normalize import normalize_key, normalize_display
from services.vocab.service import vocab_service, feature_enabled
from services.vocab.occurrences import occurrences_feature_enabled, reindex_property

__all__ = [
    "expand_query_terms",
    "MAX_EXPANDED_KEYS",
    "normalize_key",
    "normalize_display",
    "vocab_service",
    "feature_enabled",
    "occurrences_feature_enabled",
    "reindex_property",
]


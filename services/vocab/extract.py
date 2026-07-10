"""Deterministic term extraction from allowlisted CRM text fields."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from services.vocab.normalize import normalize_key

# Multi-word phrases checked before unigrams (normalized keys)
_DEFAULT_PHRASES = (
    "square meters",
    "square feet",
    "for sale",
    "for rent",
)

_TOKEN_SPLIT = re.compile(r"[^\w]+", re.UNICODE)


@dataclass
class ExtractedTerm:
    normalized_key: str
    confidence: float = 1.0


def source_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _tokens(text: str) -> List[str]:
    raw = normalize_key(text)
    if not raw:
        return []
    parts = [p for p in _TOKEN_SPLIT.split(raw) if p and len(p) >= 2]
    return parts


def extract_keys_from_text(
    text: str,
    *,
    lexicon_keys: Optional[Set[str]] = None,
    phrases: Sequence[str] = _DEFAULT_PHRASES,
) -> List[ExtractedTerm]:
    """
    Extract normalized keys from free text.
    If lexicon_keys provided, only emit keys present in lexicon (or synonyms map keys).
    Otherwise emit all tokens length >= 2 (capped).
    """
    if not (text or "").strip():
        return []
    raw_norm = normalize_key(text)
    found: Dict[str, float] = {}

    # phrases
    for ph in phrases:
        pk = normalize_key(ph)
        if pk and pk in raw_norm:
            if lexicon_keys is None or pk in lexicon_keys:
                found[pk] = max(found.get(pk, 0.0), 0.95)

    for tok in _tokens(text):
        if lexicon_keys is not None and tok not in lexicon_keys:
            continue
        found[tok] = max(found.get(tok, 0.0), 0.9 if lexicon_keys else 0.7)

    # cap
    items = sorted(found.items(), key=lambda x: (-x[1], x[0]))[:40]
    return [ExtractedTerm(normalized_key=k, confidence=c) for k, c in items]


PROPERTY_EXTRACT_FIELDS = (
    "title",
    "neighborhood",
    "property_features",
    "description",
)
CUSTOMER_EXTRACT_FIELDS = (
    "preferred_type",
    "location_preference",
)

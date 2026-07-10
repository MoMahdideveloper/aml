"""Pure string normalization for vocabulary keys."""

from __future__ import annotations

import re
import unicodedata


_WS_RE = re.compile(r"\s+")
_EDGE_PUNCT_RE = re.compile(r"^[\W_]+|[\W_]+$", re.UNICODE)


def normalize_display(text: str) -> str:
    """Collapse whitespace; preserve casing for display (canonical)."""
    if text is None:
        return ""
    s = unicodedata.normalize("NFKC", str(text))
    s = _WS_RE.sub(" ", s).strip()
    return s


def normalize_key(text: str) -> str:
    """
    Token/key normalizer:
    NFKC → strip → collapse ws → casefold → strip edge punctuation.
    Empty input → empty string.
    """
    s = normalize_display(text)
    if not s:
        return ""
    s = s.casefold()
    s = _EDGE_PUNCT_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

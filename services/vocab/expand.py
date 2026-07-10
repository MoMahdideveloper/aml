"""Query token expansion: replacement then synonym, capped."""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Sequence, Set

from services.vocab.normalize import normalize_key

MAX_EXPANDED_KEYS = 8


def _apply_replacement(token_key: str, replacements: Mapping[str, str]) -> str:
    if not token_key:
        return token_key
    return replacements.get(token_key, token_key)


def _synonyms_for(key: str, synonym_groups: Mapping[str, Sequence[str]]) -> Set[str]:
    """synonym_groups maps any member → full group list including itself."""
    out: Set[str] = {key}
    group = synonym_groups.get(key)
    if group:
        out.update(g for g in group if g)
    return out


def expand_query_terms(
    query: str,
    *,
    replacements: Mapping[str, str] | None = None,
    synonym_groups: Mapping[str, Sequence[str]] | None = None,
    max_keys: int = MAX_EXPANDED_KEYS,
) -> List[str]:
    """
    Expand a free-text query into normalized keys for SQL OR matching.

    Order: tokenize → normalize each → directional replacement → synonym expand.
    Original normalized full query is always included first when non-empty.
    Result length ≤ max_keys (default 8).
    """
    replacements = replacements or {}
    synonym_groups = synonym_groups or {}
    max_keys = max(1, int(max_keys))

    raw = (query or "").strip()
    if not raw:
        return []

    ordered: List[str] = []
    seen: Set[str] = set()

    def _add(k: str) -> None:
        if not k or k in seen:
            return
        if len(ordered) >= max_keys:
            return
        seen.add(k)
        ordered.append(k)

    full_key = normalize_key(raw)
    if full_key:
        full_after = _apply_replacement(full_key, replacements)
        for k in _synonyms_for(full_after, synonym_groups):
            _add(k)
        # also keep pre-replacement full key if different
        _add(full_key)

    for part in raw.split():
        if len(ordered) >= max_keys:
            break
        tk = normalize_key(part)
        if not tk:
            continue
        after = _apply_replacement(tk, replacements)
        for k in _synonyms_for(after, synonym_groups):
            _add(k)
        _add(tk)

    return ordered

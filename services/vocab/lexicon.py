"""In-process cache of active vocabulary maps."""

from __future__ import annotations

import threading
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_lock = threading.Lock()
_cache: Optional[Tuple[Dict[str, str], Dict[str, List[str]], float]] = None
_CACHE_TTL_SEC = 60.0


def invalidate_lexicon_cache() -> None:
    global _cache
    with _lock:
        _cache = None


def load_lexicon_maps(
    *,
    force: bool = False,
) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    Returns (replacements from_key→to_key, synonym_groups member→group list).
    Highest-priority replacement wins when multiple from_key rows exist.
    """
    global _cache
    now = time.monotonic()
    with _lock:
        if not force and _cache is not None:
            replacements, groups, loaded_at = _cache
            if now - loaded_at < _CACHE_TTL_SEC:
                return replacements, groups

    replacements, groups = _load_from_db()
    with _lock:
        _cache = (replacements, groups, now)
    return replacements, groups


def _load_from_db() -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    from sqlalchemy_models import VocabReplacement, VocabSynonym, VocabTerm

    replacements: Dict[str, str] = {}
    # collect (from_key, priority, to_key) then pick max priority
    repl_rows = (
        VocabReplacement.query.filter(VocabReplacement.status == "active")
        .order_by(VocabReplacement.priority.desc(), VocabReplacement.id.asc())
        .all()
    )
    for row in repl_rows:
        if row.from_key and row.to_key and row.from_key not in replacements:
            replacements[row.from_key] = row.to_key

    # Build undirected groups for bidirectional synonyms; one-way only term→syn
    groups: Dict[str, set] = {}

    def _link(a: str, b: str) -> None:
        if not a or not b:
            return
        groups.setdefault(a, {a}).add(b)
        groups.setdefault(b, {b}).add(a)

    terms = VocabTerm.query.filter(VocabTerm.status == "active").all()
    term_by_id = {t.id: t for t in terms}
    for t in terms:
        groups.setdefault(t.normalized_key, {t.normalized_key})

    syns = VocabSynonym.query.filter(VocabSynonym.status == "active").all()
    for s in syns:
        term = term_by_id.get(s.term_id)
        if not term or term.status != "active":
            continue
        if s.bidirectional:
            _link(term.normalized_key, s.synonym_key)
        else:
            # directional: synonym expands to term; term expands to synonym
            groups.setdefault(s.synonym_key, {s.synonym_key}).add(term.normalized_key)
            groups.setdefault(term.normalized_key, {term.normalized_key}).add(s.synonym_key)

    # freeze as lists
    frozen: Dict[str, List[str]] = {k: sorted(v) for k, v in groups.items()}
    return replacements, frozen


def maps_from_fixtures(
    replacements: Mapping[str, str] | None = None,
    synonym_groups: Mapping[str, Sequence[str]] | None = None,
) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """Test helper: build maps without DB."""
    r = dict(replacements or {})
    g = {k: list(v) for k, v in (synonym_groups or {}).items()}
    return r, g

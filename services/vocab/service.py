"""Vocab CRUD and expand orchestration."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from database import db
from services.vocab.expand import expand_query_terms, MAX_EXPANDED_KEYS
from services.vocab.lexicon import invalidate_lexicon_cache, load_lexicon_maps
from services.vocab.normalize import normalize_display, normalize_key
from sqlalchemy_models import VocabRelatedTerm, VocabReplacement, VocabSynonym, VocabTerm
from utils.observability import log_event



class VocabError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def feature_enabled() -> bool:
    try:
        from services.intelligence_settings import is_enabled

        return is_enabled("vocab_enrichment")
    except Exception:
        return os.environ.get("ENABLE_VOCAB_ENRICHMENT", "0").strip() == "1"



def expand_for_search(query: str) -> List[str]:
    """Expand query when enrichment flag is on; otherwise return [normalized] or []."""
    q = (query or "").strip()
    if not q:
        return []
    if not feature_enabled():
        # preserve prior behavior: callers use raw normalized query string as-is
        return [q]
    try:
        replacements, groups = load_lexicon_maps()
        keys = expand_query_terms(
            q, replacements=replacements, synonym_groups=groups, max_keys=MAX_EXPANDED_KEYS
        )
        # Prefer original display form of full query first for exact file_code match
        out: List[str] = []
        seen = set()
        if q not in seen:
            out.append(q)
            seen.add(q)
        for k in keys:
            if k not in seen:
                out.append(k)
                seen.add(k)
            if len(out) >= MAX_EXPANDED_KEYS:
                break
        return out or [q]
    except Exception:
        # never break search on lexicon failure
        log_event(
            "vocab_expand_failed",
            component="vocab",
            # no raw query
        )
        return [q]


class VocabService:
    def list_terms(self, *, include_archived: bool = False) -> List[Dict[str, Any]]:
        q = VocabTerm.query
        if not include_archived:
            q = q.filter(VocabTerm.status == "active")
        rows = q.order_by(VocabTerm.canonical.asc()).all()
        return [self._term_dict(t) for t in rows]

    def list_replacements(self, *, include_archived: bool = False) -> List[Dict[str, Any]]:
        q = VocabReplacement.query
        if not include_archived:
            q = q.filter(VocabReplacement.status == "active")
        rows = q.order_by(VocabReplacement.priority.desc(), VocabReplacement.id.asc()).all()
        return [
            {
                "id": r.id,
                "from_key": r.from_key,
                "to_key": r.to_key,
                "priority": r.priority,
                "status": r.status,
            }
            for r in rows
        ]

    def create_term(self, canonical: str, *, lang: str = "en") -> VocabTerm:
        display = normalize_display(canonical)
        key = normalize_key(canonical)
        if not key:
            raise VocabError("empty", "Term cannot be empty")
        if len(display) > 120 or len(key) > 120:
            raise VocabError("too_long", "Term exceeds 120 characters")
        existing = VocabTerm.query.filter_by(normalized_key=key).first()
        if existing:
            if existing.status == "archived":
                existing.status = "active"
                existing.canonical = display
                existing.lang = (lang or "en")[:8]
                db.session.commit()
                invalidate_lexicon_cache()
                log_event("vocab_term_reactivated", component="vocab", term_id=existing.id)
                return existing
            raise VocabError("duplicate", f"Term already exists: {key}")
        term = VocabTerm(
            canonical=display,
            normalized_key=key,
            lang=(lang or "en")[:8],
            status="active",
        )
        db.session.add(term)
        db.session.commit()
        invalidate_lexicon_cache()
        log_event("vocab_term_created", component="vocab", term_id=term.id)
        return term

    def archive_term(self, term_id: int) -> None:
        term = db.session.get(VocabTerm, term_id)
        if not term:
            raise VocabError("not_found", "Term not found")
        term.status = "archived"
        db.session.commit()
        invalidate_lexicon_cache()
        log_event("vocab_term_archived", component="vocab", term_id=term_id)

    def add_synonym(
        self, term_id: int, synonym: str, *, bidirectional: bool = True
    ) -> VocabSynonym:
        term = db.session.get(VocabTerm, term_id)
        if not term or term.status != "active":
            raise VocabError("not_found", "Active term not found")
        sk = normalize_key(synonym)
        if not sk:
            raise VocabError("empty", "Synonym cannot be empty")
        if sk == term.normalized_key:
            raise VocabError("same_as_term", "Synonym must differ from term")
        if len(sk) > 120:
            raise VocabError("too_long", "Synonym exceeds 120 characters")
        existing = VocabSynonym.query.filter_by(term_id=term_id, synonym_key=sk).first()
        if existing:
            if existing.status == "archived":
                existing.status = "active"
                existing.bidirectional = bool(bidirectional)
                db.session.commit()
                invalidate_lexicon_cache()
                log_event(
                    "vocab_synonym_reactivated",
                    component="vocab",
                    term_id=term_id,
                    synonym_id=existing.id,
                )
                return existing
            raise VocabError("duplicate", "Synonym already exists for term")
        row = VocabSynonym(
            term_id=term_id,
            synonym_key=sk,
            bidirectional=bool(bidirectional),
            status="active",
        )
        db.session.add(row)
        db.session.commit()
        invalidate_lexicon_cache()
        log_event(
            "vocab_synonym_created",
            component="vocab",
            term_id=term_id,
            synonym_id=row.id,
        )
        return row

    def archive_synonym(self, synonym_id: int) -> None:
        row = db.session.get(VocabSynonym, synonym_id)
        if not row:
            raise VocabError("not_found", "Synonym not found")
        row.status = "archived"
        db.session.commit()
        invalidate_lexicon_cache()
        log_event("vocab_synonym_archived", component="vocab", synonym_id=synonym_id)

    def _replacement_would_cycle(self, from_key: str, to_key: str) -> bool:
        """True if adding from→to creates a cycle in active replacements."""
        graph: Dict[str, str] = {}
        for r in VocabReplacement.query.filter_by(status="active").all():
            if r.from_key and r.to_key:
                graph[r.from_key] = r.to_key
        graph[from_key] = to_key
        seen = set()
        cur = to_key
        for _ in range(32):
            if cur == from_key:
                return True
            if cur in seen or cur not in graph:
                break
            seen.add(cur)
            cur = graph[cur]
        return False

    def create_replacement(
        self, from_text: str, to_text: str, *, priority: int = 0
    ) -> VocabReplacement:
        fk = normalize_key(from_text)
        tk = normalize_key(to_text)
        if not fk or not tk:
            raise VocabError("empty", "Both from and to are required")
        if fk == tk:
            raise VocabError("same", "from and to must differ")
        if self._replacement_would_cycle(fk, tk):
            raise VocabError("cycle", "Replacement would create a cycle")
        existing = VocabReplacement.query.filter_by(from_key=fk, to_key=tk).first()
        if existing:
            if existing.status == "archived":
                if self._replacement_would_cycle(fk, tk):
                    raise VocabError("cycle", "Replacement would create a cycle")
                existing.status = "active"
                existing.priority = int(priority or 0)
                db.session.commit()
                invalidate_lexicon_cache()
                log_event(
                    "vocab_replacement_reactivated",
                    component="vocab",
                    replacement_id=existing.id,
                )
                return existing
            raise VocabError("duplicate", "Replacement already exists")
        row = VocabReplacement(
            from_key=fk,
            to_key=tk,
            priority=int(priority or 0),
            status="active",
        )
        db.session.add(row)
        db.session.commit()
        invalidate_lexicon_cache()
        log_event(
            "vocab_replacement_created",
            component="vocab",
            replacement_id=row.id,
        )
        return row


    def archive_replacement(self, replacement_id: int) -> None:
        row = db.session.get(VocabReplacement, replacement_id)
        if not row:
            raise VocabError("not_found", "Replacement not found")
        row.status = "archived"
        db.session.commit()
        invalidate_lexicon_cache()
        log_event(
            "vocab_replacement_archived",
            component="vocab",
            replacement_id=replacement_id,
        )

    def add_related(self, term_id: int, related: str) -> VocabRelatedTerm:
        """Non-equivalent association — never used for query expansion."""
        term = db.session.get(VocabTerm, term_id)
        if not term or term.status != "active":
            raise VocabError("not_found", "Active term not found")
        rk = normalize_key(related)
        if not rk:
            raise VocabError("empty", "Related term cannot be empty")
        if rk == term.normalized_key:
            raise VocabError("same_as_term", "Related must differ from term")
        existing = VocabRelatedTerm.query.filter_by(term_id=term_id, related_key=rk).first()
        if existing:
            if existing.status == "archived":
                existing.status = "active"
                db.session.commit()
                return existing
            raise VocabError("duplicate", "Related term already exists")
        row = VocabRelatedTerm(term_id=term_id, related_key=rk, status="active")
        db.session.add(row)
        db.session.commit()
        log_event("vocab_related_created", component="vocab", term_id=term_id, related_id=row.id)
        return row

    def archive_related(self, related_id: int) -> None:
        row = db.session.get(VocabRelatedTerm, related_id)
        if not row:
            raise VocabError("not_found", "Related term not found")
        row.status = "archived"
        db.session.commit()
        log_event("vocab_related_archived", component="vocab", related_id=related_id)

    def _term_dict(self, term: VocabTerm) -> Dict[str, Any]:
        syns = [
            {
                "id": s.id,
                "synonym_key": s.synonym_key,
                "bidirectional": s.bidirectional,
                "status": s.status,
            }
            for s in (term.synonyms or [])
            if s.status == "active"
        ]
        related = [
            {"id": r.id, "related_key": r.related_key, "status": r.status}
            for r in VocabRelatedTerm.query.filter_by(term_id=term.id, status="active").all()
        ]
        return {
            "id": term.id,
            "canonical": term.canonical,
            "normalized_key": term.normalized_key,
            "lang": term.lang,
            "status": term.status,
            "synonyms": syns,
            "related": related,
        }



vocab_service = VocabService()

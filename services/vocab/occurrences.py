"""Persist and refresh vocab_occurrences (never mutates source entity text)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Set

from database import db
from services.vocab.extract import (
    CUSTOMER_EXTRACT_FIELDS,
    PROPERTY_EXTRACT_FIELDS,
    extract_keys_from_text,
    source_hash,
)
from services.vocab.lexicon import load_lexicon_maps
from sqlalchemy_models import Customer, Property, VocabOccurrence, VocabTerm, _utcnow_naive
from utils.observability import log_event


def occurrences_feature_enabled() -> bool:
    try:
        from services.intelligence_settings import is_enabled

        return is_enabled("vocab_occurrences")
    except Exception:
        return os.environ.get("ENABLE_VOCAB_OCCURRENCES", "0").strip() == "1"



def _lexicon_key_set() -> Set[str]:
    replacements, groups = load_lexicon_maps()
    keys: Set[str] = set(replacements.keys()) | set(replacements.values())
    for member, group in groups.items():
        keys.add(member)
        keys.update(group)
    # also all active term keys
    for t in VocabTerm.query.filter_by(status="active").all():
        keys.add(t.normalized_key)
    return keys


def _term_id_for_key(key: str, cache: Dict[str, Optional[int]]) -> Optional[int]:
    if key in cache:
        return cache[key]
    row = VocabTerm.query.filter_by(normalized_key=key, status="active").first()
    cache[key] = row.id if row else None
    return cache[key]


def reindex_property(property_id: int, *, require_lexicon: bool = True) -> Dict[str, Any]:
    prop = Property.query.filter_by(id=property_id, is_deleted=False).first()
    if not prop:
        return {"status": "not_found", "entity_type": "property", "entity_id": property_id}

    lexicon = _lexicon_key_set() if require_lexicon else None
    if require_lexicon and not lexicon:
        # still allow extraction of empty if no lexicon — no-op
        pass

    term_cache: Dict[str, Optional[int]] = {}
    written = 0
    for field in PROPERTY_EXTRACT_FIELDS:
        text = getattr(prop, field, None) or ""
        sh = source_hash(str(text))
        extracted = extract_keys_from_text(str(text), lexicon_keys=lexicon if require_lexicon else None)
        keys_now = {e.normalized_key for e in extracted}

        existing = VocabOccurrence.query.filter_by(
            entity_type="property", entity_id=property_id, field=field
        ).all()
        by_key = {o.normalized_key: o for o in existing}

        for e in extracted:
            tid = _term_id_for_key(e.normalized_key, term_cache)
            row = by_key.get(e.normalized_key)
            if row:
                row.confidence = e.confidence
                row.status = "active"
                row.source_hash = sh
                row.term_id = tid
                row.extracted_at = _utcnow_naive()
            else:
                db.session.add(
                    VocabOccurrence(
                        entity_type="property",
                        entity_id=property_id,
                        field=field,
                        term_id=tid,
                        normalized_key=e.normalized_key,
                        confidence=e.confidence,
                        status="active",
                        source_hash=sh,
                        extracted_at=_utcnow_naive(),
                    )
                )
            written += 1

        for key, row in by_key.items():
            if key not in keys_now:
                if row.source_hash != sh:
                    row.status = "stale"
                else:
                    row.status = "stale"

    db.session.commit()
    log_event(
        "vocab_occurrences_reindexed",
        component="vocab",
        entity_type="property",
        entity_id=property_id,
        written=written,
    )
    return {"status": "ok", "entity_type": "property", "entity_id": property_id, "written": written}


def reindex_customer(customer_id: int, *, require_lexicon: bool = True) -> Dict[str, Any]:
    cust = Customer.query.filter_by(id=customer_id, is_deleted=False).first()
    if not cust:
        return {"status": "not_found", "entity_type": "customer", "entity_id": customer_id}

    lexicon = _lexicon_key_set() if require_lexicon else None
    term_cache: Dict[str, Optional[int]] = {}
    written = 0
    for field in CUSTOMER_EXTRACT_FIELDS:
        text = getattr(cust, field, None) or ""
        sh = source_hash(str(text))
        extracted = extract_keys_from_text(str(text), lexicon_keys=lexicon if require_lexicon else None)
        keys_now = {e.normalized_key for e in extracted}
        existing = VocabOccurrence.query.filter_by(
            entity_type="customer", entity_id=customer_id, field=field
        ).all()
        by_key = {o.normalized_key: o for o in existing}
        for e in extracted:
            tid = _term_id_for_key(e.normalized_key, term_cache)
            row = by_key.get(e.normalized_key)
            if row:
                row.confidence = e.confidence
                row.status = "active"
                row.source_hash = sh
                row.term_id = tid
                row.extracted_at = _utcnow_naive()
            else:
                db.session.add(
                    VocabOccurrence(
                        entity_type="customer",
                        entity_id=customer_id,
                        field=field,
                        term_id=tid,
                        normalized_key=e.normalized_key,
                        confidence=e.confidence,
                        status="active",
                        source_hash=sh,
                        extracted_at=_utcnow_naive(),
                    )
                )
            written += 1
        for key, row in by_key.items():
            if key not in keys_now:
                row.status = "stale"
    db.session.commit()
    log_event(
        "vocab_occurrences_reindexed",
        component="vocab",
        entity_type="customer",
        entity_id=customer_id,
        written=written,
    )
    return {"status": "ok", "entity_type": "customer", "entity_id": customer_id, "written": written}


def list_for_entity(entity_type: str, entity_id: int, *, active_only: bool = True) -> List[Dict[str, Any]]:
    q = VocabOccurrence.query.filter_by(entity_type=entity_type, entity_id=entity_id)
    if active_only:
        q = q.filter(VocabOccurrence.status == "active")
    rows = q.order_by(VocabOccurrence.confidence.desc(), VocabOccurrence.normalized_key.asc()).all()
    return [
        {
            "normalized_key": r.normalized_key,
            "field": r.field,
            "term_id": r.term_id,
            "confidence": r.confidence,
            "status": r.status,
        }
        for r in rows
    ]


def reindex_batch_properties(limit: int = 50) -> Dict[str, Any]:
    props = (
        Property.query.filter_by(is_deleted=False)
        .order_by(Property.id.asc())
        .limit(max(1, min(limit, 500)))
        .all()
    )
    ok = 0
    for p in props:
        r = reindex_property(p.id)
        if r.get("status") == "ok":
            ok += 1
    return {"status": "ok", "processed": len(props), "ok": ok}

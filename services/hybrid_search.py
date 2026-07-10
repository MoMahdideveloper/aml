"""Hybrid CRM search: keyword (unified) + optional semantic property ranking."""

from __future__ import annotations

import json
import math
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy_models import Property, PropertyEmbedding
from services.query_constraints import extract_constraints, property_matches_hard
from services.unified_search import SearchRequest, unified_search_service
from utils.observability import log_event, record_business_counter

KEYWORD_WEIGHT = 0.45
SEMANTIC_WEIGHT = 0.55
SEMANTIC_CANDIDATE_LIMIT = 200
RRF_K = 60


def feature_enabled() -> bool:
    return os.environ.get("ENABLE_HYBRID_SEARCH", "0").strip() == "1"


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    if n <= 0:
        return 0.0
    dot = sum(float(a[i]) * float(b[i]) for i in range(n))
    na = math.sqrt(sum(float(a[i]) ** 2 for i in range(n)))
    nb = math.sqrt(sum(float(b[i]) ** 2 for i in range(n)))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def rrf_merge(
    keyword_ranked_ids: Sequence[int],
    semantic_ranked_ids: Sequence[int],
    *,
    k: int = RRF_K,
) -> List[Tuple[int, float]]:
    """Reciprocal rank fusion; returns (id, score) sorted desc."""
    scores: Dict[int, float] = {}
    for rank, pid in enumerate(keyword_ranked_ids, start=1):
        scores[pid] = scores.get(pid, 0.0) + 1.0 / (k + rank)
    for rank, pid in enumerate(semantic_ranked_ids, start=1):
        scores[pid] = scores.get(pid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def weighted_merge(
    keyword_scores: Dict[int, float],
    semantic_scores: Dict[int, float],
    *,
    kw_w: float = KEYWORD_WEIGHT,
    sem_w: float = SEMANTIC_WEIGHT,
) -> List[Tuple[int, float]]:
    """Normalize each map to 0..1 by max then weighted sum."""
    ids = set(keyword_scores) | set(semantic_scores)
    if not ids:
        return []
    kmax = max(keyword_scores.values()) if keyword_scores else 1.0
    smax = max(semantic_scores.values()) if semantic_scores else 1.0
    kmax = kmax or 1.0
    smax = smax or 1.0
    out: List[Tuple[int, float]] = []
    for pid in ids:
        kn = (keyword_scores.get(pid, 0.0) / kmax) if kmax else 0.0
        sn = (semantic_scores.get(pid, 0.0) / smax) if smax else 0.0
        out.append((pid, kn * kw_w + sn * sem_w))
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def _load_embedding_json(raw: str) -> List[float]:
    try:
        parsed = json.loads(raw or "[]")
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _embed_query(text: str) -> Tuple[List[float], bool, str]:
    """
    Returns (vector, degraded, reason).
    Always uses provider embed (includes hash fallback) unless exception.
    """
    try:
        from services.embeddings import embedding_provider

        vecs = embedding_provider.embed([text])
        if not vecs or not vecs[0]:
            return [], True, "empty_embedding"
        degraded = not getattr(embedding_provider, "is_available", True)
        return list(vecs[0]), degraded, ("provider_hash_fallback" if degraded else "ok")
    except Exception:
        return [], True, "embed_exception"


def _semantic_scores_for_query(
    query: str,
    *,
    property_ids: Optional[Sequence[int]] = None,
    limit: int = SEMANTIC_CANDIDATE_LIMIT,
) -> Tuple[Dict[int, float], bool, str]:
    """Score stored property embeddings vs query. Degrades if none/embed fail."""
    qvec, degraded, reason = _embed_query(query)
    if not qvec:
        return {}, True, reason

    q = PropertyEmbedding.query
    if property_ids:
        q = q.filter(PropertyEmbedding.property_id.in_(list(property_ids)))
    rows = q.limit(limit).all()
    if not rows:
        return {}, True, "no_property_embeddings"

    scores: Dict[int, float] = {}
    for row in rows:
        vec = _load_embedding_json(row.embedding_data)
        if not vec:
            continue
        sim = _cosine(qvec, vec)
        if sim > 0:
            scores[int(row.property_id)] = float(sim)
    if not scores:
        return {}, True, "no_positive_similarity"
    return scores, degraded, reason


def _keyword_score_from_tier(rank_tier: int, position: int) -> float:
    # lower tier better; position 0-based within group
    tier_part = max(0.0, 4.0 - float(rank_tier if rank_tier < 90 else 3))
    pos_part = 1.0 / (1.0 + position)
    return tier_part + pos_part


def _hit_dict_from_property(prop: Property, *, matched_field: str, rank_tier: int) -> Dict[str, Any]:
    from services.unified_search import _entity_url

    sub = prop.address or ""
    if prop.file_code:
        sub = f"{prop.file_code} · {sub}"
    return {
        "entity_type": "properties",
        "id": prop.id,
        "title": prop.title or f"Property #{prop.id}",
        "subtitle": sub[:200],
        "status": prop.status or "",
        "url": _entity_url("properties", prop.id),
        "matched_field": matched_field,
        "rank_tier": rank_tier,
    }


class HybridSearchService:
    def search(self, req: SearchRequest) -> Dict[str, Any]:
        t0 = time.perf_counter()
        base = unified_search_service.search(req)

        hybrid_meta: Dict[str, Any] = {
            "enabled": False,
            "mode": "keyword_only",
            "degraded": False,
            "reason": "",
            "chips": [],
            "constraints": {},
        }

        if not feature_enabled():
            base["hybrid"] = hybrid_meta
            return base

        # Autocomplete stays keyword-only for latency
        if req.mode == "autocomplete":
            hybrid_meta["reason"] = "autocomplete_keyword_only"
            base["hybrid"] = hybrid_meta
            return base

        if "properties" not in req.scopes:
            hybrid_meta["reason"] = "properties_not_in_scope"
            base["hybrid"] = hybrid_meta
            return base

        constraints = extract_constraints(req.normalized_query)
        hard = constraints.hard_filters()
        chips = list(constraints.chips())

        # Start from keyword property hits
        kw_hits: List[Dict[str, Any]] = list(base.get("groups", {}).get("properties") or [])
        kw_ids = [int(h["id"]) for h in kw_hits if h.get("id") is not None]
        keyword_scores: Dict[int, float] = {}
        for i, h in enumerate(kw_hits):
            pid = int(h["id"])
            keyword_scores[pid] = _keyword_score_from_tier(int(h.get("rank_tier") or 99), i)

        # Apply hard filters to keyword hits
        if hard and kw_ids:
            props = {
                p.id: p
                for p in Property.query.filter(
                    Property.id.in_(kw_ids), Property.is_deleted.is_(False)
                ).all()
            }
            filtered = []
            for h in kw_hits:
                p = props.get(int(h["id"]))
                if p is not None and property_matches_hard(p, hard):
                    filtered.append(h)
            kw_hits = filtered
            kw_ids = [int(h["id"]) for h in kw_hits]
            keyword_scores = {pid: keyword_scores[pid] for pid in kw_ids if pid in keyword_scores}

        # Hard-filter SQL candidates (when free-text keyword misses structured intent)
        hard_props: List[Property] = []
        if hard:
            q = Property.query.filter(Property.is_deleted.is_(False))
            if hard.get("property_type"):
                q = q.filter(Property.property_type.ilike(f"%{hard['property_type']}%"))
            if hard.get("bedrooms_min") is not None:
                q = q.filter(Property.bedrooms >= int(hard["bedrooms_min"]))
            if hard.get("price_max") is not None:
                q = q.filter(Property.price <= float(hard["price_max"]))
            if hard.get("price_min") is not None:
                q = q.filter(Property.price >= float(hard["price_min"]))
            if hard.get("listing_type"):
                lt = str(hard["listing_type"])
                if lt in ("rent", "rental"):
                    q = q.filter(Property.listing_type.in_(["rent", "rental"]))
                else:
                    q = q.filter(Property.listing_type.ilike(f"%{lt}%"))
            hard_props = q.order_by(Property.id.asc()).limit(80).all()
            for p in hard_props:
                if p.id not in keyword_scores:
                    # weak base score so structured-only matches still surface
                    keyword_scores[p.id] = 0.15

        # Semantic branch
        semantic_scores: Dict[int, float] = {}
        degraded = False
        reason = "ok"
        try:
            candidate_ids = list(dict.fromkeys(kw_ids + [p.id for p in hard_props]))
            semantic_scores, degraded, reason = _semantic_scores_for_query(
                req.normalized_query,
                property_ids=candidate_ids if candidate_ids else None,
            )
            # filter semantic by hard
            if hard and semantic_scores:
                props = {
                    p.id: p
                    for p in Property.query.filter(
                        Property.id.in_(list(semantic_scores.keys())),
                        Property.is_deleted.is_(False),
                    ).all()
                }
                semantic_scores = {
                    pid: sc
                    for pid, sc in semantic_scores.items()
                    if pid in props and property_matches_hard(props[pid], hard)
                }
        except Exception:
            semantic_scores = {}
            degraded = True
            reason = "semantic_exception"

        # hash fallback still yields vectors — allow hybrid if scores exist
        use_semantic = bool(semantic_scores)

        if use_semantic:
            merged = weighted_merge(keyword_scores, semantic_scores)
            mode = "hybrid"
            chips.append("Semantic ranking")
        else:
            merged = [(pid, keyword_scores.get(pid, 0.0)) for pid in keyword_scores]
            merged.sort(key=lambda x: (-x[1], x[0]))
            mode = "keyword_only"
            degraded = True
            if reason == "ok":
                reason = "no_semantic_scores"

        # Build property hit list in merged order; keep keyword hit payloads when present
        by_id = {int(h["id"]): h for h in kw_hits}
        for p in hard_props:
            if p.id not in by_id:
                by_id[p.id] = _hit_dict_from_property(
                    p, matched_field="constraint", rank_tier=4
                )
        need_load = [pid for pid, _ in merged if pid not in by_id]
        if need_load:
            for p in Property.query.filter(
                Property.id.in_(need_load), Property.is_deleted.is_(False)
            ).all():
                by_id[p.id] = _hit_dict_from_property(
                    p, matched_field="semantic", rank_tier=3
                )


        per_page = req.per_page
        page = req.page
        start = (page - 1) * per_page
        end = start + per_page
        page_ids = [pid for pid, _ in merged[start:end]]
        new_props: List[Dict[str, Any]] = []
        # Expanded keys used (normalized keys only — never raw query log)
        expanded_keys: List[str] = []
        try:
            from services.vocab.service import expand_for_search, feature_enabled as vocab_on

            if vocab_on() and req.normalized_query:
                expanded_keys = expand_for_search(req.normalized_query)[:12]
        except Exception:
            expanded_keys = []

        for pid in page_ids:
            h = by_id.get(pid)
            if not h:
                continue
            h = dict(h)
            if pid in semantic_scores:
                h["semantic_score"] = round(semantic_scores[pid], 4)
            if pid in keyword_scores:
                h["keyword_score"] = round(keyword_scores[pid], 4)
            why_parts: List[str] = []
            if pid in keyword_scores:
                why_parts.append(f"keyword field={h.get('matched_field') or 'text'}")
            if pid in semantic_scores:
                why_parts.append("semantic similarity")
            if hard:
                why_parts.append("hard filters applied")
            if use_semantic and pid in semantic_scores and pid not in keyword_scores:
                h["matched_field"] = h.get("matched_field") or "semantic"
                h["explain"] = "semantic"
            elif use_semantic and pid in semantic_scores and pid in keyword_scores:
                h["explain"] = "keyword+semantic"
            elif h.get("matched_field") == "constraint":
                h["explain"] = "constraint"
            h["evidence"] = {
                "matched_field": h.get("matched_field") or "",
                "keyword_score": h.get("keyword_score"),
                "semantic_score": h.get("semantic_score"),
                "filters_hard": hard,
                "filters_soft": constraints.soft_filters(),
                "expanded_term_count": len(expanded_keys),
                # keys only if short; avoid dumping large expansions
                "expanded_terms_sample": expanded_keys[:6],
                "why": "; ".join(why_parts) if why_parts else "ranked result",
            }
            new_props.append(h)

        base.setdefault("groups", {})["properties"] = new_props
        base.setdefault("counts", {})["properties"] = len(new_props)
        # recompute total across groups
        base["total_count"] = sum(len(base["groups"].get(k) or []) for k in base["groups"])

        if constraints.chips():
            chips = list(dict.fromkeys(chips + constraints.chips()))

        hybrid_meta = {
            "enabled": True,
            "mode": mode,
            "degraded": degraded and mode == "keyword_only",
            "reason": reason,
            "chips": chips,
            "constraints": constraints.to_public_dict(),
            "semantic_hit_count": len(semantic_scores),
            "keyword_hit_count": len(keyword_scores),
            "expanded_term_count": len(expanded_keys),
        }
        base["hybrid"] = hybrid_meta


        duration_ms = int((time.perf_counter() - t0) * 1000)
        log_event(
            "hybrid_search_completed",
            component="hybrid_search",
            duration_ms=duration_ms,
            mode=mode,
            degraded=hybrid_meta["degraded"],
            reason=reason,
            # no raw query
        )
        record_business_counter(
            "crm_hybrid_search_total",
            outcome=mode if not hybrid_meta["degraded"] else "degraded",
        )
        return base


hybrid_search_service = HybridSearchService()


def search(req: SearchRequest) -> Dict[str, Any]:
    return hybrid_search_service.search(req)

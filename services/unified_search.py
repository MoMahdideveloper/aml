"""Unified Track A CRM search (SQLAlchemy only, no external search)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from flask import url_for
from sqlalchemy import and_, cast, func, or_, String
from sqlalchemy.orm import joinedload

from database import db
from sqlalchemy_models import Agent, Customer, Deal, Property, Task
from utils.observability import log_event, record_business_counter

ENTITY_SCOPES = ("customers", "properties", "deals", "agents", "tasks")
MIN_QUERY_LEN = 2
MAX_QUERY_LEN = 100
AUTOCOMPLETE_PER_GROUP = 5
FULL_PER_PAGE = 20
SORTS = ("relevance", "id", "title")

# Customer saved-view allowlist (versioned)
SAVED_VIEW_SCHEMA_VERSION = 1
CUSTOMER_FILTER_KEYS = frozenset(
    {"q", "status", "customer_type", "sort", "page"}
)


class SearchValidationError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class SearchRequest:
    query: str
    scopes: Set[str]
    status: Optional[str] = None
    agent_id: Optional[int] = None
    customer_type: Optional[str] = None
    page: int = 1
    per_page: int = FULL_PER_PAGE
    sort: str = "relevance"
    mode: str = "full"  # full | autocomplete
    actor_id: Optional[int] = None

    @property
    def normalized_query(self) -> str:
        return re.sub(r"\s+", " ", (self.query or "").strip())


@dataclass
class SearchHit:
    entity_type: str
    id: int
    title: str
    subtitle: str
    status: str
    url: str
    matched_field: str = ""
    rank_tier: int = 99  # lower better

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "status": self.status,
            "url": self.url,
            "matched_field": self.matched_field,
        }


def feature_enabled() -> bool:
    import os

    return os.environ.get("ENABLE_GLOBAL_SEARCH", "1").strip() != "0"


def parse_search_request(
    *,
    q: Optional[str],
    scope: Optional[str] = None,
    status: Optional[str] = None,
    agent_id: Optional[str] = None,
    customer_type: Optional[str] = None,
    page: Optional[str] = None,
    per_page: Optional[str] = None,
    sort: Optional[str] = None,
    mode: str = "full",
    actor_id: Optional[int] = None,
    unknown_keys: Optional[Sequence[str]] = None,
) -> SearchRequest:
    # ignore unknown client fields (caller may pass request.args)
    raw = (q or "").strip()
    if len(raw) > MAX_QUERY_LEN:
        raise SearchValidationError("too_long", f"Query exceeds {MAX_QUERY_LEN} characters")

    is_numeric_id = raw.isdigit() and len(raw) <= 12
    if raw and not is_numeric_id and len(raw) < MIN_QUERY_LEN:
        raise SearchValidationError(
            "too_short", f"Query must be at least {MIN_QUERY_LEN} characters"
        )

    scopes: Set[str]
    if scope:
        scopes = {s.strip().lower() for s in scope.split(",") if s.strip()}
        bad = scopes - set(ENTITY_SCOPES)
        if bad:
            raise SearchValidationError("bad_scope", f"Unknown entity scope: {', '.join(sorted(bad))}")
        if not scopes:
            scopes = set(ENTITY_SCOPES)
    else:
        scopes = set(ENTITY_SCOPES)

    sort_v = (sort or "relevance").strip().lower()
    if sort_v not in SORTS:
        raise SearchValidationError("bad_sort", f"Invalid sort: {sort_v}")

    try:
        page_i = max(1, int(page or 1))
    except (TypeError, ValueError):
        raise SearchValidationError("bad_page", "Invalid page") from None
    try:
        pp = int(per_page or (AUTOCOMPLETE_PER_GROUP if mode == "autocomplete" else FULL_PER_PAGE))
    except (TypeError, ValueError):
        raise SearchValidationError("bad_limit", "Invalid per_page") from None
    if mode == "autocomplete":
        pp = min(max(1, pp), AUTOCOMPLETE_PER_GROUP)
    else:
        pp = min(max(1, pp), FULL_PER_PAGE)

    aid: Optional[int] = None
    if agent_id not in (None, ""):
        try:
            aid = int(agent_id)
        except (TypeError, ValueError):
            raise SearchValidationError("bad_agent", "Invalid agent_id") from None

    return SearchRequest(
        query=raw,
        scopes=scopes,
        status=(status or "").strip() or None,
        agent_id=aid,
        customer_type=(customer_type or "").strip().lower() or None,
        page=page_i,
        per_page=pp,
        sort=sort_v,
        mode=mode,
        actor_id=actor_id,
    )


def _digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")


def _entity_url(entity: str, entity_id: int) -> str:
    """Server-side destination paths (work outside request context for tests)."""
    try:
        if entity == "customers":
            try:
                return url_for("customers.customer_360", customer_id=entity_id)
            except Exception:
                return f"/customers/{entity_id}"
        if entity == "properties":
            return url_for("properties.view_property", property_id=entity_id)
        if entity == "deals":
            return url_for("deals.deals", highlight=entity_id)
        if entity == "agents":
            return url_for("agents.agent_dashboard", agent_id=entity_id)
        if entity == "tasks":
            return url_for("tasks.tasks", highlight=entity_id)
    except Exception:
        pass
    # Fallback absolute-path style (deterministic, no host)
    paths = {
        "customers": f"/customers/{entity_id}",
        "properties": f"/properties/{entity_id}",
        "deals": f"/deals?highlight={entity_id}",
        "agents": f"/agents/{entity_id}",
        "tasks": f"/tasks?highlight={entity_id}",
    }
    return paths.get(entity, f"/{entity}/{entity_id}")


def _ilike(col, pattern: str):
    # SQLite: LIKE is case-insensitive for ASCII by default for unquoted
    return col.ilike(pattern) if hasattr(col, "ilike") else col.like(pattern)


def _tier_for_text(q: str, *, exact_vals: Sequence[str], prefix_vals: Sequence[str], contains_vals: Sequence[str]) -> Tuple[int, str]:
    ql = q.lower()
    for v in exact_vals:
        if v and v.lower() == ql:
            return 1, "exact"
    for v in prefix_vals:
        if v and v.lower().startswith(ql):
            return 2, "prefix"
    for v in contains_vals:
        if v and ql in v.lower():
            return 3, "contains"
    return 99, ""


def _best_tier_for_terms(
    terms: Sequence[str],
    *,
    exact_vals: Sequence[str],
    prefix_vals: Sequence[str],
    contains_vals: Sequence[str],
) -> Tuple[int, str]:
    best_tier, best_field = 99, ""
    for t in terms:
        if not t:
            continue
        tier, field = _tier_for_text(
            t, exact_vals=exact_vals, prefix_vals=prefix_vals, contains_vals=contains_vals
        )
        if tier < best_tier:
            best_tier, best_field = tier, field
            if best_tier <= 1:
                break
    return best_tier, best_field


def _property_search_terms(q: str) -> Tuple[List[str], bool, int]:
    """
    Terms used for property keyword OR match.
    When vocab enrichment is off, returns [q] only (legacy behavior).
    """
    if not q:
        return [], False, 0
    try:
        from services.vocab.service import expand_for_search, feature_enabled

        if not feature_enabled():
            return [q], False, 0
        terms = expand_for_search(q)
        return terms, True, max(0, len(terms) - 1)
    except Exception:
        return [q], False, 0



class SearchRepository:
    """Bounded entity queries; only allowlisted columns selected via model attrs."""

    def search_customers(self, req: SearchRequest) -> List[SearchHit]:
        q = req.normalized_query
        query = Customer.query.filter(Customer.is_deleted.is_(False))
        if req.status:
            query = query.filter(Customer.status == req.status)
        if req.customer_type:
            query = query.filter(Customer.customer_type == req.customer_type)

        if q:
            clauses = []
            if q.isdigit():
                clauses.append(Customer.id == int(q))
            like = f"%{q}%"
            prefix = f"{q}%"
            clauses.extend(
                [
                    Customer.email == q.lower(),
                    Customer.email.ilike(prefix),
                    Customer.name.ilike(prefix),
                    Customer.name.ilike(like),
                    Customer.email.ilike(like),
                    Customer.phone.ilike(like),
                    Customer.location_preference.ilike(like),
                ]
            )
            dig = _digits(q)
            if dig and len(dig) >= 3:
                clauses.append(Customer.phone.ilike(f"%{dig}%"))
            query = query.filter(or_(*clauses))

        rows = (
            query.order_by(Customer.id.asc())
            .limit(req.per_page * 3)  # rank in Python within bound
            .all()
        )
        hits: List[SearchHit] = []
        for c in rows:
            tier, matched = 0, "id"
            if q and str(c.id) == q:
                tier, matched = 0, "id"
            else:
                tier, matched = _tier_for_text(
                    q,
                    exact_vals=[c.email or ""],
                    prefix_vals=[c.name or "", c.email or ""],
                    contains_vals=[
                        c.name or "",
                        c.email or "",
                        c.phone or "",
                        c.location_preference or "",
                    ],
                )
            hits.append(
                SearchHit(
                    entity_type="customers",
                    id=c.id,
                    title=c.name or f"Customer #{c.id}",
                    subtitle=f"{c.email or ''} · {c.phone or ''}".strip(" ·"),
                    status=c.status or "",
                    url=_entity_url("customers", c.id),
                    matched_field=matched,
                    rank_tier=tier,
                )
            )
        return self._finalize(hits, req)

    def search_properties(self, req: SearchRequest) -> List[SearchHit]:
        q = req.normalized_query
        terms, _vocab_on, _extra = _property_search_terms(q)
        query = Property.query.filter(Property.is_deleted.is_(False))
        if req.status:
            query = query.filter(Property.status == req.status)
        if req.agent_id:
            query = query.filter(Property.agent_id == req.agent_id)
        if q:
            clauses = []
            if q.isdigit():
                clauses.append(Property.id == int(q))
            for term in terms:
                if not term:
                    continue
                like = f"%{term}%"
                prefix = f"{term}%"
                clauses.extend(
                    [
                        Property.file_code == term,
                        Property.file_code.ilike(prefix),
                        Property.title.ilike(prefix),
                        Property.title.ilike(like),
                        Property.address.ilike(like),
                        Property.neighborhood.ilike(like),
                    ]
                )
            if clauses:
                query = query.filter(or_(*clauses))
        rows = query.order_by(Property.id.asc()).limit(req.per_page * 3).all()
        hits = []
        rank_terms = terms or ([q] if q else [])
        for p in rows:
            if q and str(p.id) == q:
                tier, matched = 0, "id"
            elif q and any(
                (p.file_code or "").lower() == (t or "").lower() for t in rank_terms
            ):
                tier, matched = 1, "file_code"
            else:
                tier, matched = _best_tier_for_terms(
                    rank_terms,
                    exact_vals=[p.file_code or ""],
                    prefix_vals=[p.title or "", p.file_code or ""],
                    contains_vals=[p.title or "", p.address or "", p.neighborhood or ""],
                )
            sub = p.address or ""
            if p.file_code:
                sub = f"{p.file_code} · {sub}"
            hits.append(
                SearchHit(
                    entity_type="properties",
                    id=p.id,
                    title=p.title or f"Property #{p.id}",
                    subtitle=sub[:200],
                    status=p.status or "",
                    url=_entity_url("properties", p.id),
                    matched_field=matched,
                    rank_tier=tier,
                )
            )
        return self._finalize(hits, req)


    def search_deals(self, req: SearchRequest) -> List[SearchHit]:
        q = req.normalized_query
        query = (
            Deal.query.filter(Deal.is_deleted.is_(False))
            .options(joinedload(Deal.property), joinedload(Deal.customer))
        )
        if req.status:
            query = query.filter(Deal.status == req.status)
        if req.agent_id:
            query = query.filter(Deal.agent_id == req.agent_id)
        if q:
            clauses = []
            if q.isdigit():
                clauses.append(Deal.id == int(q))
            like = f"%{q}%"
            clauses.append(Deal.status.ilike(like))
            # join filters via EXISTS-style using relationships after load — filter in SQL
            query = query.outerjoin(Property, Deal.property_id == Property.id).outerjoin(
                Customer, Deal.customer_id == Customer.id
            )
            clauses.extend(
                [
                    Property.title.ilike(like),
                    Property.file_code.ilike(like),
                    Customer.name.ilike(like),
                    Customer.email.ilike(like),
                ]
            )
            query = query.filter(or_(*clauses))
        rows = query.order_by(Deal.id.asc()).limit(req.per_page * 3).all()
        hits = []
        for d in rows:
            ptitle = d.property.title if d.property else f"P#{d.property_id}"
            cname = d.customer.name if d.customer else f"C#{d.customer_id}"
            if q and str(d.id) == q:
                tier, matched = 0, "id"
            else:
                tier, matched = _tier_for_text(
                    q,
                    exact_vals=[],
                    prefix_vals=[ptitle, cname],
                    contains_vals=[ptitle, cname, d.status or ""],
                )
            hits.append(
                SearchHit(
                    entity_type="deals",
                    id=d.id,
                    title=f"Deal #{d.id} · {d.status}",
                    subtitle=f"{ptitle} · {cname}",
                    status=d.status or "",
                    url=_entity_url("deals", d.id),
                    matched_field=matched,
                    rank_tier=tier,
                )
            )
        return self._finalize(hits, req)

    def search_agents(self, req: SearchRequest) -> List[SearchHit]:
        q = req.normalized_query
        query = Agent.query.filter(Agent.is_deleted.is_(False))
        if q:
            clauses = []
            if q.isdigit():
                clauses.append(Agent.id == int(q))
            like = f"%{q}%"
            prefix = f"{q}%"
            clauses.extend(
                [
                    Agent.email == q.lower(),
                    Agent.email.ilike(prefix),
                    Agent.name.ilike(prefix),
                    Agent.name.ilike(like),
                    Agent.email.ilike(like),
                    Agent.phone.ilike(like),
                    Agent.specialization.ilike(like),
                ]
            )
            query = query.filter(or_(*clauses))
        rows = query.order_by(Agent.id.asc()).limit(req.per_page * 3).all()
        hits = []
        for a in rows:
            if q and str(a.id) == q:
                tier, matched = 0, "id"
            else:
                tier, matched = _tier_for_text(
                    q,
                    exact_vals=[a.email or ""],
                    prefix_vals=[a.name or "", a.email or ""],
                    contains_vals=[a.name or "", a.email or "", a.phone or "", a.specialization or ""],
                )
            hits.append(
                SearchHit(
                    entity_type="agents",
                    id=a.id,
                    title=a.name or f"Agent #{a.id}",
                    subtitle=f"{a.email or ''} · {a.specialization or ''}".strip(" ·"),
                    status="active",
                    url=_entity_url("agents", a.id),
                    matched_field=matched,
                    rank_tier=tier,
                )
            )
        return self._finalize(hits, req)

    def search_tasks(self, req: SearchRequest) -> List[SearchHit]:
        q = req.normalized_query
        query = Task.query.filter(Task.is_deleted.is_(False))
        if req.status:
            query = query.filter(Task.status == req.status)
        if req.agent_id:
            query = query.filter(Task.agent_id == req.agent_id)
        if q:
            clauses = []
            if q.isdigit():
                clauses.append(Task.id == int(q))
            like = f"%{q}%"
            prefix = f"{q}%"
            clauses.extend(
                [
                    Task.title.ilike(prefix),
                    Task.title.ilike(like),
                    Task.status.ilike(like),
                    Task.priority.ilike(like),
                ]
            )
            query = query.filter(or_(*clauses))
        rows = query.order_by(Task.id.asc()).limit(req.per_page * 3).all()
        hits = []
        for t in rows:
            if q and str(t.id) == q:
                tier, matched = 0, "id"
            else:
                tier, matched = _tier_for_text(
                    q,
                    exact_vals=[],
                    prefix_vals=[t.title or ""],
                    contains_vals=[t.title or "", t.status or "", t.priority or ""],
                )
            hits.append(
                SearchHit(
                    entity_type="tasks",
                    id=t.id,
                    title=t.title or f"Task #{t.id}",
                    subtitle=f"{t.status} · {t.priority}",
                    status=t.status or "",
                    url=_entity_url("tasks", t.id),
                    matched_field=matched,
                    rank_tier=tier,
                )
            )
        return self._finalize(hits, req)

    def _finalize(self, hits: List[SearchHit], req: SearchRequest) -> List[SearchHit]:
        if req.sort == "id":
            hits.sort(key=lambda h: h.id)
        elif req.sort == "title":
            hits.sort(key=lambda h: (h.title.lower(), h.id))
        else:
            hits.sort(key=lambda h: (h.rank_tier, h.id))
        # pagination for full mode per group
        start = (req.page - 1) * req.per_page
        end = start + req.per_page
        return hits[start:end]


class UnifiedSearchService:
    def __init__(self):
        self.repo = SearchRepository()

    def search(self, req: SearchRequest) -> Dict[str, Any]:
        t0 = time.perf_counter()
        groups: Dict[str, List[Dict[str, Any]]] = {k: [] for k in ENTITY_SCOPES}
        counts: Dict[str, int] = {k: 0 for k in ENTITY_SCOPES}

        # empty free-text: only return empty groups unless filters alone (skip free-text entities without filter)
        runners = {
            "customers": self.repo.search_customers,
            "properties": self.repo.search_properties,
            "deals": self.repo.search_deals,
            "agents": self.repo.search_agents,
            "tasks": self.repo.search_tasks,
        }
        for scope in ENTITY_SCOPES:
            if scope not in req.scopes:
                continue
            if not req.normalized_query and not req.status and not req.agent_id and not req.customer_type:
                continue
            # agents without query and without filters: skip
            if scope == "agents" and not req.normalized_query:
                continue
            hits = runners[scope](req)
            groups[scope] = [h.to_dict() for h in hits]
            counts[scope] = len(hits)

        total = sum(counts.values())
        duration_ms = int((time.perf_counter() - t0) * 1000)
        vocab_expanded = False
        expanded_term_count = 0
        if "properties" in req.scopes and req.normalized_query:
            _terms, vocab_expanded, expanded_term_count = _property_search_terms(
                req.normalized_query
            )
        log_event(
            "search_completed",
            component="search",
            duration_ms=duration_ms,
            total_count=total,
            zero_results=total == 0,
            scope_count=len(req.scopes),
            mode=req.mode,
            vocab_expanded=vocab_expanded,
            expanded_term_count=expanded_term_count,
            # deliberately no query text
        )
        record_business_counter("crm_search_total", outcome="ok" if total else "zero")
        return {
            "query": req.normalized_query,
            "total_count": total,
            "groups": groups,
            "counts": counts,
            "page": req.page,
            "per_page": req.per_page,
            "sort": req.sort,
            "scopes": sorted(req.scopes),
            "vocab_expanded": vocab_expanded,
            "expanded_term_count": expanded_term_count,
        }


unified_search_service = UnifiedSearchService()
